# api/caldav.py

import logging
import uuid
import pytz
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from fastapi import Request, Response, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from api.caldav_router import CalDAVRouter
from core.dependencies import get_db_session
from core.database import (
    AgendaEvent,
    Account,
    Task,
    Workspace,
    WorkspacePermission,
)
from utils.security import get_current_account_id_caldav
from icalendar import Calendar, Event, Todo, vDatetime

from core.agenda_manager import (
    get_event_by_caldav_uid,
    update_event_db,
    schedule_event,
    cancel_event,
    get_events_as_dicts,
)
from core.tasks_manager import (
    create_task,
    delete_task,
    get_task_by_caldav_uid,
    get_tasks_as_dicts,
    update_task_db as update_task_core,
)

logger = logging.getLogger(__name__)
router = CalDAVRouter()

# --- Helpers ---

def _get_workspace_id_from_cal(calendar_id: str) -> Optional[uuid.UUID]:
    if calendar_id in ["default", "personal"]:
        return None
    try:
        return uuid.UUID(calendar_id)
    except ValueError:
        return None

def _pretty_print_xml(elem: ET.Element) -> str:
    xml_str = ET.tostring(elem, encoding="utf-8").decode("utf-8")
    return '<?xml version="1.0" encoding="utf-8"?>' + xml_str

# --- iCalendar Converters ---

def _event_to_ical(event: AgendaEvent, account_timezone: str) -> str:
    cal = Calendar()
    cal.add("prodid", "-//KognitoAI//NONSGML v1.0//EN")
    cal.add("version", "2.0")
    ical_event = Event()
    uid = event.caldav_uid if event.caldav_uid else str(event.id)
    ical_event.add("uid", uid)
    ical_event.add("summary", event.summary)
    
    user_tz = pytz.timezone(account_timezone)
    dtstart_local = event.event_datetime_utc.astimezone(user_tz)
    ical_event.add("dtstart", vDatetime(dtstart_local))
    
    duration = event.duration_minutes or 60
    ical_event.add("dtend", vDatetime(dtstart_local + timedelta(minutes=duration)))
    ical_event.add("dtstamp", vDatetime(datetime.now(pytz.utc)))
    
    if event.description: ical_event.add("description", event.description)
    if event.location: ical_event.add("location", event.location)
    
    cal.add_component(ical_event)
    return cal.to_ical().decode("utf-8")

def _task_to_ical(task: Task, account_timezone: str) -> str:
    cal = Calendar()
    cal.add("prodid", "-//KognitoAI//NONSGML v1.0//EN")
    cal.add("version", "2.0")
    ical_todo = Todo()
    uid = task.caldav_uid if task.caldav_uid else str(task.id)
    ical_todo.add("uid", uid)
    ical_todo.add("summary", task.description)
    
    user_tz = pytz.timezone(account_timezone)
    if task.end_date:
        ical_todo.add("due", vDatetime(task.end_date.astimezone(user_tz)))
    if task.start_date:
        ical_todo.add("dtstart", vDatetime(task.start_date.astimezone(user_tz)))
        
    if task.is_completed:
        ical_todo.add("status", "COMPLETED")
    elif task.status == "En Progreso":
        ical_todo.add("status", "IN-PROCESS")
    else:
        ical_todo.add("status", "NEEDS-ACTION")
        
    ical_todo.add("dtstamp", vDatetime(datetime.now(pytz.utc)))
    cal.add_component(ical_todo)
    return cal.to_ical().decode("utf-8")

async def _ical_to_event_data(ical_data: bytes, account_id: str, db: AsyncSession) -> Dict[str, Any]:
    cal = Calendar.from_ical(ical_data)
    for component in cal.walk():
        if component.name == "VEVENT":
            dtstart = component.get("dtstart")
            account = await db.get(Account, uuid.UUID(account_id))
            user_tz = pytz.timezone(account.timezone) if account and account.timezone else pytz.utc
            
            dt_local = dtstart.dt.astimezone(user_tz) if hasattr(dtstart.dt, "tzinfo") and dtstart.dt.tzinfo else user_tz.localize(dtstart.dt)
            
            return {
                "summary": str(component.get("summary", "")),
                "description": str(component.get("description", "")),
                "location": str(component.get("location", "")),
                "event_date": dt_local.strftime("%Y-%m-%d"),
                "event_time": dt_local.strftime("%H:%M"),
                "duration_minutes": int(component.get("duration").dt.total_seconds() / 60) if component.get("duration") else 60
            }
    return {}

async def _ical_to_task_data(ical_data: bytes, account_id: str, db: AsyncSession) -> Dict[str, Any]:
    cal = Calendar.from_ical(ical_data)
    for component in cal.walk():
        if component.name == "VTODO":
            return {
                "description": str(component.get("summary", "")),
                "is_completed": str(component.get("status", "")).upper() == "COMPLETED",
                "status": "En Progreso" if str(component.get("status", "")).upper() == "IN-PROCESS" else "Pendiente"
            }
    return {}

# --- Root & Principal Endpoints ---

@router.options("/caldav")
@router.options("/caldav/")
async def options_caldav_root():
    response = Response(status_code=200)
    response.headers["DAV"] = "1, 2, calendar-access, calendar-proxy"
    response.headers["Allow"] = "OPTIONS, GET, HEAD, POST, PUT, DELETE, PROPFIND, REPORT, PROPPATCH"
    return response

@router.propfind("/caldav", status_code=207)
@router.propfind("/caldav/", status_code=207)
async def propfind_caldav_root(current_account_id: str = Depends(get_current_account_id_caldav)):
    DAV_NS = "DAV:"
    ET.register_namespace("D", DAV_NS)
    multistatus = ET.Element(f"{{{DAV_NS}}}multistatus")
    resp = ET.SubElement(multistatus, f"{{{DAV_NS}}}response")
    ET.SubElement(resp, f"{{{DAV_NS}}}href").text = "/api/caldav/"
    pstat = ET.SubElement(resp, f"{{{DAV_NS}}}propstat")
    prop = ET.SubElement(pstat, f"{{{DAV_NS}}}prop")
    ET.SubElement(ET.SubElement(prop, f"{{{DAV_NS}}}resourcetype"), f"{{{DAV_NS}}}collection")
    principal_href = f"/api/caldav/principals/{current_account_id}/"
    ET.SubElement(ET.SubElement(prop, f"{{{DAV_NS}}}current-user-principal"), f"{{{DAV_NS}}}href").text = principal_href
    ET.SubElement(pstat, f"{{{DAV_NS}}}status").text = "HTTP/1.1 200 OK"
    return Response(content=_pretty_print_xml(multistatus), status_code=207, media_type="application/xml")

@router.propfind("/caldav/principals/{account_id}", status_code=207)
@router.propfind("/caldav/principals/{account_id}/", status_code=207)
async def propfind_caldav_principal(account_id: str, current_account_id: str = Depends(get_current_account_id_caldav)):
    if account_id != current_account_id: raise HTTPException(status_code=403)
    DAV_NS = "DAV:"
    CALDAV_NS = "urn:ietf:params:xml:ns:caldav"
    ET.register_namespace("D", DAV_NS)
    ET.register_namespace("C", CALDAV_NS)
    multistatus = ET.Element(f"{{{DAV_NS}}}multistatus")
    resp = ET.SubElement(multistatus, f"{{{DAV_NS}}}response")
    ET.SubElement(resp, f"{{{DAV_NS}}}href").text = f"/api/caldav/principals/{account_id}/"
    pstat = ET.SubElement(resp, f"{{{DAV_NS}}}propstat")
    prop = ET.SubElement(pstat, f"{{{DAV_NS}}}prop")
    rt = ET.SubElement(prop, f"{{{DAV_NS}}}resourcetype")
    ET.SubElement(rt, f"{{{DAV_NS}}}principal")
    ET.SubElement(rt, f"{{{DAV_NS}}}collection")
    ET.SubElement(ET.SubElement(prop, f"{{{CALDAV_NS}}}calendar-home-set"), f"{{{DAV_NS}}}href").text = f"/api/caldav/calendars/{account_id}/"
    ET.SubElement(pstat, f"{{{DAV_NS}}}status").text = "HTTP/1.1 200 OK"
    return Response(content=_pretty_print_xml(multistatus), status_code=207, media_type="application/xml")

# --- Home-Set & Collection Endpoints ---

@router.propfind("/caldav/calendars/{account_id}", status_code=207)
@router.propfind("/caldav/calendars/{account_id}/", status_code=207)
async def propfind_caldav_home_set(
    account_id: str,
    current_account_id: str = Depends(get_current_account_id_caldav),
    db: AsyncSession = Depends(get_db_session)
):
    if account_id != current_account_id: raise HTTPException(status_code=403)
    ET.register_namespace("D", "DAV:")
    ET.register_namespace("C", "urn:ietf:params:xml:ns:caldav")
    multistatus = ET.Element("{DAV:}multistatus")
    
    # Home response
    hr = ET.SubElement(multistatus, "{DAV:}response")
    ET.SubElement(hr, "{DAV:}href").text = f"/api/caldav/calendars/{account_id}/"
    hp_ps = ET.SubElement(hr, "{DAV:}propstat")
    hp = ET.SubElement(hp_ps, "{DAV:}prop")
    ET.SubElement(ET.SubElement(hp, "{DAV:}resourcetype"), "{DAV:}collection")
    ET.SubElement(hp_ps, "{DAV:}status").text = "HTTP/1.1 200 OK"

    # Calendars: Personal + Workspaces
    cals = [("default", "Calendario Principal"), ("personal", "Personal")]
    stmt = select(Workspace).join(WorkspacePermission).where(WorkspacePermission.account_id == uuid.UUID(current_account_id))
    workspaces = (await db.execute(stmt)).scalars().all()
    for ws in workspaces: cals.append((str(ws.id), f"Workspace: {ws.name}"))

    for cid, name in cals:
        cr = ET.SubElement(multistatus, "{DAV:}response")
        ET.SubElement(cr, "{DAV:}href").text = f"/api/caldav/calendars/{account_id}/{cid}/"
        cp_ps = ET.SubElement(cr, "{DAV:}propstat")
        cp = ET.SubElement(cp_ps, "{DAV:}prop")
        rt = ET.SubElement(cp, "{DAV:}resourcetype")
        ET.SubElement(rt, "{DAV:}collection")
        ET.SubElement(rt, "{urn:ietf:params:xml:ns:caldav}calendar")
        ET.SubElement(cp, "{DAV:}displayname").text = name
        
        # Add supported component types (VEVENT, VTODO)
        sccs = ET.SubElement(cp, "{urn:ietf:params:xml:ns:caldav}supported-calendar-component-set")
        ET.SubElement(sccs, "{urn:ietf:params:xml:ns:caldav}comp", name="VEVENT")
        ET.SubElement(sccs, "{urn:ietf:params:xml:ns:caldav}comp", name="VTODO")
        
        ctag = ET.SubElement(cp, "{http://calendarserver.org/ns/}getctag")
        ctag.text = str(int(datetime.now().timestamp()))
        ET.SubElement(cp_ps, "{DAV:}status").text = "HTTP/1.1 200 OK"

    return Response(content=_pretty_print_xml(multistatus), status_code=207, media_type="application/xml")

@router.options("/caldav/calendars/{account_id}/{calendar_id}")
@router.options("/caldav/calendars/{account_id}/{calendar_id}/")
async def options_caldav_calendar_collection():
    resp = Response(status_code=200)
    resp.headers["Allow"] = "OPTIONS, GET, HEAD, POST, PUT, DELETE, PROPFIND, REPORT, PROPPATCH"
    resp.headers["DAV"] = "1, 2, calendar-access"
    return resp

@router.propfind("/caldav/calendars/{account_id}/{calendar_id}", status_code=207)
@router.propfind("/caldav/calendars/{account_id}/{calendar_id}/", status_code=207)
async def propfind_caldav_calendar_collection(
    account_id: str, calendar_id: str, request: Request,
    current_account_id: str = Depends(get_current_account_id_caldav),
    db: AsyncSession = Depends(get_db_session)
):
    if account_id != current_account_id: raise HTTPException(status_code=403)
    logger.info(f"PROPFIND/REPORT for account {account_id}, calendar {calendar_id}")
    workspace_id = _get_workspace_id_from_cal(calendar_id)
    
    ET.register_namespace("D", "DAV:")
    ET.register_namespace("C", "urn:ietf:params:xml:ns:caldav")
    
    body = await request.body()
    wants_data = b"calendar-data" in body.lower()
    
    multiget_hrefs = None
    if b"calendar-multiget" in body.lower() and body:
        try:
            root_el = ET.fromstring(body)
            href_elements = root_el.findall(".//{DAV:}href") or root_el.findall(".//href")
            if not href_elements:
                href_elements = [el for el in root_el.iter() if el.tag.endswith("}href") or el.tag == "href"]
            multiget_hrefs = {el.text.strip() for el in href_elements if el.text}
        except Exception as e:
            logger.warning(f"Error parsing calendar-multiget body: {e}")
            
    multistatus = ET.Element("{DAV:}multistatus")
    if multiget_hrefs is None:
        # Collection itself response
        resp = ET.SubElement(multistatus, "{DAV:}response")
        ET.SubElement(resp, "{DAV:}href").text = request.url.path
        ps = ET.SubElement(resp, "{DAV:}propstat")
        prop = ET.SubElement(ps, "{DAV:}prop")
        rt = ET.SubElement(prop, "{DAV:}resourcetype")
        ET.SubElement(rt, "{DAV:}collection")
        ET.SubElement(rt, "{urn:ietf:params:xml:ns:caldav}calendar")
        
        # Add supported component types (VEVENT, VTODO)
        sccs = ET.SubElement(prop, "{urn:ietf:params:xml:ns:caldav}supported-calendar-component-set")
        ET.SubElement(sccs, "{urn:ietf:params:xml:ns:caldav}comp", name="VEVENT")
        ET.SubElement(sccs, "{urn:ietf:params:xml:ns:caldav}comp", name="VTODO")
        
        ET.SubElement(ps, "{DAV:}status").text = "HTTP/1.1 200 OK"

    body_lower = body.lower() if body else b""
    has_filter = b"comp-filter" in body_lower or b"comp" in body_lower
    
    include_events = True
    include_tasks = True
    
    if has_filter:
        has_vevent = b"vevent" in body_lower
        has_vtodo = b"vtodo" in body_lower
        if has_vevent and not has_vtodo:
            include_tasks = False
        elif has_vtodo and not has_vevent:
            include_events = False

    events = []
    if include_events:
        events = await get_events_as_dicts(current_account_id, workspace_id=calendar_id, include_past=True)
        
    tasks = []
    if include_tasks:
        tasks = await get_tasks_as_dicts(current_account_id, include_completed=True, workspace_id=calendar_id)
        
    account = await db.get(Account, uuid.UUID(current_account_id))
    tz = account.timezone if account and account.timezone else "UTC"

    for items, to_ical_func, model in [(events, _event_to_ical, AgendaEvent), (tasks, _task_to_ical, Task)]:
        for item in items:
            uid = item.get("caldav_uid") or str(item["id"])
            item_href = f"{request.url.path.rstrip('/')}/{uid}.ics"
            
            if multiget_hrefs is not None:
                matched = False
                for h in multiget_hrefs:
                    if h.endswith(f"/{uid}.ics") or h.endswith(f"/{uid}"):
                        matched = True
                        break
                if not matched:
                    continue
                    
            logger.debug(f"Processing item {item.get('id')} for CalDAV response")
            ir = ET.SubElement(multistatus, "{DAV:}response")
            ET.SubElement(ir, "{DAV:}href").text = item_href
            ps = ET.SubElement(ir, "{DAV:}propstat")
            prop = ET.SubElement(ps, "{DAV:}prop")
            
            etag_val = item.get("etag")
            if not etag_val:
                etag_val = f'"{item["id"]}-static"'
            ET.SubElement(prop, "{DAV:}getetag").text = str(etag_val)
            
            if wants_data:
                # Convert ID to UUID if it's a string (for Tasks)
                search_id = item["id"]
                if isinstance(search_id, str):
                    try: search_id = uuid.UUID(search_id)
                    except: pass
                
                obj = await db.get(model, search_id)
                if obj:
                    ET.SubElement(prop, "{urn:ietf:params:xml:ns:caldav}calendar-data").text = to_ical_func(obj, tz) # type: ignore
            ET.SubElement(ps, "{DAV:}status").text = "HTTP/1.1 200 OK"

    return Response(content=_pretty_print_xml(multistatus), status_code=207, media_type="application/xml")

@router.report("/caldav/calendars/{account_id}/{calendar_id}", status_code=207)
@router.report("/caldav/calendars/{account_id}/{calendar_id}/", status_code=207)
async def report_caldav_calendar_collection(
    account_id: str, calendar_id: str, request: Request,
    current_account_id: str = Depends(get_current_account_id_caldav),
    db: AsyncSession = Depends(get_db_session)
):
    return await propfind_caldav_calendar_collection(account_id, calendar_id, request, current_account_id, db)

# --- Resource Endpoints ---

@router.get("/caldav/calendars/{account_id}/{calendar_id}/{uid}.ics")
async def get_caldav_resource(
    account_id: str, calendar_id: str, uid: str,
    current_account_id: str = Depends(get_current_account_id_caldav),
    db: AsyncSession = Depends(get_db_session)
):
    if account_id != current_account_id: raise HTTPException(status_code=403)
    ws_id = _get_workspace_id_from_cal(calendar_id)
    
    res = await get_event_by_caldav_uid(current_account_id, uid)
    tp = "event"
    if not res and uid.isdigit():
        stmt = select(AgendaEvent).options(
            selectinload(AgendaEvent.contact_profiles),
            selectinload(AgendaEvent.workspace),
            selectinload(AgendaEvent.attendees)
        ).where(
            AgendaEvent.id == int(uid),
            AgendaEvent.account_id == uuid.UUID(current_account_id)
        )
        res = (await db.execute(stmt)).scalars().first()
        
    if not res:
        res = await get_task_by_caldav_uid(current_account_id, uid)
        tp = "task"
        if not res:
            try:
                task_uuid = uuid.UUID(uid)
                stmt = select(Task).options(selectinload(Task.contact_profiles)).where(
                    Task.id == task_uuid,
                    Task.account_id == uuid.UUID(current_account_id)
                )
                res = (await db.execute(stmt)).scalars().first()
                tp = "task"
            except ValueError:
                pass
    
    if not res or res.workspace_id != ws_id: raise HTTPException(status_code=404)
    
    account = await db.get(Account, uuid.UUID(current_account_id))
    tz = account.timezone if account and account.timezone else "UTC"
    content = _event_to_ical(res, tz) if tp == "event" else _task_to_ical(res, tz)
    return Response(content=content, media_type="text/calendar")

@router.put("/caldav/calendars/{account_id}/{calendar_id}/{uid}.ics")
async def put_caldav_resource(
    account_id: str, calendar_id: str, uid: str, request: Request,
    current_account_id: str = Depends(get_current_account_id_caldav),
    db: AsyncSession = Depends(get_db_session)
):
    if account_id != current_account_id: raise HTTPException(status_code=403)
    ws_id = _get_workspace_id_from_cal(calendar_id)
    body = await request.body()
    is_todo = b"VTODO" in body
    
    if is_todo:
        data = await _ical_to_task_data(body, current_account_id, db)
        existing = await get_task_by_caldav_uid(current_account_id, uid)
        if not existing:
            try:
                task_uuid = uuid.UUID(uid)
                stmt = select(Task).options(selectinload(Task.contact_profiles)).where(
                    Task.id == task_uuid,
                    Task.account_id == uuid.UUID(current_account_id)
                )
                existing = (await db.execute(stmt)).scalars().first()
            except ValueError:
                pass
        if existing:
            if existing.workspace_id != ws_id: raise HTTPException(status_code=403)
            obj = await update_task_core(db, current_account_id, str(existing.id), **data)
        else:
            _, _, obj = await create_task(account_id=current_account_id, workspace_id=ws_id, caldav_uid=uid, **data)
    else:
        data = await _ical_to_event_data(body, current_account_id, db)
        existing = await get_event_by_caldav_uid(current_account_id, uid)
        if not existing and uid.isdigit():
            stmt = select(AgendaEvent).options(
                selectinload(AgendaEvent.contact_profiles),
                selectinload(AgendaEvent.workspace),
                selectinload(AgendaEvent.attendees)
            ).where(
                AgendaEvent.id == int(uid),
                AgendaEvent.account_id == uuid.UUID(current_account_id)
            )
            existing = (await db.execute(stmt)).scalars().first()
        if existing:
            if existing.workspace_id != ws_id: raise HTTPException(status_code=403)
            # update_event_db expects different dict than schedule_event
            account = await db.get(Account, uuid.UUID(current_account_id))
            user_tz = pytz.timezone(account.timezone) if account and account.timezone else pytz.utc
            
            event_datetime_utc = None
            if "event_date" in data and "event_time" in data:
                try:
                    local_datetime_str = f"{data['event_date']} {data['event_time']}"
                    naive_datetime = datetime.strptime(local_datetime_str, "%Y-%m-%d %H:%M")
                    localized_dt = user_tz.localize(naive_datetime)
                    event_datetime_utc = localized_dt.astimezone(pytz.utc)
                except ValueError:
                    pass

            duration_minutes = data.get("duration_minutes")
            end_date = None
            if event_datetime_utc and duration_minutes is not None:
                end_date = event_datetime_utc + timedelta(minutes=duration_minutes)

            update_fields = {
                "summary": data.get("summary"),
                "description": data.get("description"),
                "location": data.get("location"),
                "event_datetime_utc": event_datetime_utc,
                "end_date": end_date,
                "duration_minutes": duration_minutes,
            }
            # Remove None values so we don't overwrite if they are not specified
            update_fields = {k: v for k, v in update_fields.items() if v is not None}
            
            obj = await update_event_db(db, current_account_id, existing.id, **update_fields)
        else:
            _, _, obj = await schedule_event(current_account_id, workspace_id=str(ws_id) if ws_id else None, caldav_uid=uid, **data)

    if obj:
        etag = str(uuid.uuid4())
        obj.etag = etag
        await db.commit()
        return Response(status_code=201 if not existing else 200, headers={"ETag": etag})
    return Response(status_code=400)

@router.delete("/caldav/calendars/{account_id}/{calendar_id}/{uid}.ics")
async def delete_caldav_resource(
    account_id: str, calendar_id: str, uid: str,
    current_account_id: str = Depends(get_current_account_id_caldav),
    db: AsyncSession = Depends(get_db_session)
):
    if account_id != current_account_id: raise HTTPException(status_code=403)
    ws_id = _get_workspace_id_from_cal(calendar_id)
    res = await get_event_by_caldav_uid(current_account_id, uid)
    if not res and uid.isdigit():
        stmt = select(AgendaEvent).where(
            AgendaEvent.id == int(uid),
            AgendaEvent.account_id == uuid.UUID(current_account_id)
        )
        res = (await db.execute(stmt)).scalars().first()
    if res:
        if res.workspace_id == ws_id: await cancel_event(current_account_id, res.id); return Response(status_code=204)
    res = await get_task_by_caldav_uid(current_account_id, uid)
    if not res:
        try:
            task_uuid = uuid.UUID(uid)
            stmt = select(Task).where(
                Task.id == task_uuid,
                Task.account_id == uuid.UUID(current_account_id)
            )
            res = (await db.execute(stmt)).scalars().first()
        except ValueError:
            pass
    if res:
        if res.workspace_id == ws_id: await delete_task(current_account_id, res.id); return Response(status_code=204)
    raise HTTPException(status_code=404)

@router.proppatch("/caldav/calendars/{account_id}/{calendar_id}")
@router.proppatch("/caldav/calendars/{account_id}/{calendar_id}/")
async def proppatch_caldav_calendar(calendar_id: str, request: Request):
    multistatus = ET.Element("{DAV:}multistatus")
    resp = ET.SubElement(multistatus, "{DAV:}response")
    ET.SubElement(resp, "{DAV:}href").text = request.url.path
    ps = ET.SubElement(resp, "{DAV:}propstat")
    ET.SubElement(ps, "{DAV:}status").text = "HTTP/1.1 200 OK"
    return Response(content=_pretty_print_xml(multistatus), status_code=207, media_type="application/xml")
