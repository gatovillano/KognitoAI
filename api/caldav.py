# api/caldav.py

from fastapi import APIRouter, Request, Response, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db_session, AgendaEvent, Account, ContactProfile, Task # Import AgendaEvent, Account, ContactProfile, Task
from utils.security import get_current_account_id
from typing import Optional, Dict, Any, List
from icalendar import Calendar, Event, Todo, vDatetime, vText, vUri # Importar Calendar, Event, Todo, vDatetime, vText, vUri
from datetime import datetime, timedelta # Importar timedelta para el fin del evento
import pytz # Importar pytz para zonas horarias
import uuid # Importar uuid
from core.agenda_manager import get_task_by_id_db as get_event_task_by_id_db, update_task_db as update_event_task_db # Importar funciones para tareas
from core.tasks_manager import create_task, delete_task, get_task_by_id_db, update_task_db, get_tasks_as_dicts # Importar funciones de tasks_manager

router = APIRouter()

# --- Funciones auxiliares para iCalendar ---
def _event_to_ical(event: AgendaEvent, account_timezone: str) -> str:
    """
    Convierte un objeto AgendaEvent de la DB a una cadena iCalendar (VCALENDAR).
    """
    cal = Calendar()
    cal.add('prodid', '-//KognitoAI//NONSGML v1.0//EN')
    cal.add('version', '2.0')

    ical_event = Event()
    ical_event.add('uid', str(event.id))
    ical_event.add('summary', event.summary)
    
    # Manejo de DTSTART y DTEND
    user_tz = pytz.timezone(account_timezone)
    dtstart_local = event.event_datetime_utc.astimezone(user_tz)
    ical_event.add('dtstart', vDatetime(dtstart_local))
    # Para DTEND, asumimos una duración por defecto si no hay un campo de duración explícito.
    # Por ejemplo, una hora.
    if event.duration_minutes is not None:
        dtend_local = dtstart_local + timedelta(minutes=event.duration_minutes)
    else:
        dtend_local = dtstart_local + timedelta(hours=1) # Duración por defecto de 1 hora
    ical_event.add('dtend', vDatetime(dtend_local))
    
    ical_event.add('dtstamp', vDatetime(datetime.now(pytz.utc))) # Timestamp de la creación/última modificación

    if event.description:
        ical_event.add('description', event.description)
    if event.location:
        ical_event.add('location', event.location)

    # Añadir asistentes
    if event.attendees:
        for attendee in event.attendees:
            ical_event.add('attendee', f'MAILTO:{attendee.email}') # Asumiendo que Account tiene un campo email

    if event.external_attendees:
        for ext_attendee in event.external_attendees:
            ical_event.add('attendee', ext_attendee) # Podría ser un nombre o email

    # Añadir perfiles vinculados como ATENDEE o X-PROPERTY
    if event.contact_profiles:
        for profile in event.contact_profiles:
            # Podríamos usar el email si lo tienen, o un X-PROPERTY para su nombre
            ical_event.add('attendee', f'CN={profile.name};MAILTO:{profile.email}')


    cal.add_component(ical_event)
    return cal.to_ical().decode('utf-8')

def _task_to_ical(task: Task, account_timezone: str) -> str:
    """
    Convierte un objeto Task de la DB a una cadena iCalendar (VTODO).
    """
    cal = Calendar()
    cal.add('prodid', '-//KognitoAI//NONSGML v1.0//EN')
    cal.add('version', '2.0')

    ical_todo = Todo()
    ical_todo.add('uid', str(task.id))
    ical_todo.add('summary', task.description) # Usamos description como summary para Task

    user_tz = pytz.timezone(account_timezone)
    if task.due_date:
        # Asumimos que task.due_date ya está en UTC si se guarda así, o se convierte.
        # Para VTODO, DUE puede ser solo fecha o fecha y hora.
        # Si task.due_date es datetime, lo convertimos a la zona horaria del usuario.
        if isinstance(task.due_date, datetime):
            due_date_local = task.due_date.astimezone(user_tz)
            ical_todo.add('due', vDatetime(due_date_local))
        else: # Si es solo fecha
            ical_todo.add('due', task.due_date)

    if task.description:
        ical_todo.add('description', task.description)
    
    # STATUS para VTODO
    if task.is_completed:
        ical_todo.add('status', 'COMPLETED')
        ical_todo.add('completed', vDatetime(datetime.now(pytz.utc).astimezone(user_tz))) # Fecha de completado

    ical_todo.add('dtstamp', vDatetime(datetime.now(pytz.utc))) # Timestamp de la creación/última modificación

    cal.add_component(ical_todo)
    return cal.to_ical().decode('utf-8')

async def _ical_to_event_data(ical_data: bytes, account_id: str, db: AsyncSession) -> Dict[str, Any]:
    """
    Parsea una cadena iCalendar y extrae los datos relevantes para AgendaEvent.
    """
    cal = Calendar.from_ical(ical_data)
    event_data = {}
    
    # Solo tomamos el primer evento si hay múltiples en el iCalendar
    for component in cal.walk():
        if component.name == 'VEVENT':
            ical_event = component
            
            event_data['summary'] = str(ical_event.get('summary', ''))
            event_data['description'] = str(ical_event.get('description', ''))
            event_data['location'] = str(ical_event.get('location', ''))
            
            # DTSTART y DTEND
            dtstart = ical_event.get('dtstart')
            if dtstart:
                # Convertir a UTC si es necesario y luego a datetime.datetime
                if isinstance(dtstart.dt, datetime):
                    dtstart_dt = dtstart.dt
                else: # Si es date, convertir a datetime al inicio del día
                    dtstart_dt = datetime(dtstart.dt.year, dtstart.dt.month, dtstart.dt.day, 0, 0, 0)
                
                # Obtener la zona horaria del usuario para convertir correctamente
                account = await db.get(Account, uuid.UUID(account_id))
                user_tz = pytz.timezone(account.timezone) if account and account.timezone else pytz.utc
                
                if dtstart_dt.tzinfo is None: # Naive datetime, asumimos que está en la zona horaria del usuario
                    localized_dt = user_tz.localize(dtstart_dt)
                    event_data['event_datetime_utc'] = localized_dt.astimezone(pytz.utc)
                else: # Aware datetime, convertir directamente a UTC
                    event_data['event_datetime_utc'] = dtstart_dt.astimezone(pytz.utc)
            
            # UID
            event_data['id'] = str(ical_event.get('uid', uuid.uuid4())) # Usar UID existente o generar uno nuevo

            # DURATION
            duration_ical = ical_event.get('duration')
            if duration_ical:
                # La duración de iCalendar es un timedelta. Convertimos a minutos.
                event_data['duration_minutes'] = int(duration_ical.total_seconds() / 60)
            else:
                # Si no hay duración explícita, podemos intentar calcularla desde DTSTART y DTEND
                dtstart_ical = ical_event.get('dtstart')
                dtend_ical = ical_event.get('dtend')
                if dtstart_ical and dtend_ical and isinstance(dtstart_ical.dt, datetime) and isinstance(dtend_ical.dt, datetime):
                    time_difference = dtend_ical.dt - dtstart_ical.dt
                    event_data['duration_minutes'] = int(time_difference.total_seconds() / 60)
                else:
                    event_data['duration_minutes'] = None # O un valor por defecto si se prefiere
            
            # Asistentes
            attendee_emails = []
            external_attendees = []
            for attendee in ical_event.get('attendee', []):
                if 'MAILTO:' in str(attendee):
                    email = str(attendee).replace('MAILTO:', '')
                    attendee_emails.append(email)
                else:
                    external_attendees.append(str(attendee))
            
            # Buscar IDs de cuentas por email
            if attendee_emails:
                stmt = select(Account.id).where(Account.email.in_(attendee_emails))
                result = await db.execute(stmt)
                event_data['attendee_ids'] = [str(aid) for aid in result.scalars().all()]
            else:
                event_data['attendee_ids'] = []

            event_data['external_attendees'] = external_attendees
            
            # Otras propiedades como STATUS (si es VTODO, por ejemplo)
            # Por ahora, solo manejamos VEVENT.
            
            break # Solo procesamos el primer VEVENT
    
    return event_data

async def _ical_to_task_data(ical_data: bytes, account_id: str, db: AsyncSession) -> Dict[str, Any]:
    """
    Parsea una cadena iCalendar (VTODO) y extrae los datos relevantes para Task.
    """
    cal = Calendar.from_ical(ical_data)
    task_data = {}

    for component in cal.walk():
        if component.name == 'VTODO':
            ical_todo = component

            task_data['description'] = str(ical_todo.get('summary', '')) # Usamos summary de iCal como description de Task
            task_data['summary'] = str(ical_todo.get('summary', '')) # También lo guardamos en summary para compatibilidad

            # DUE date
            due = ical_todo.get('due')
            if due:
                if isinstance(due.dt, datetime):
                    task_data['due_date'] = due.dt.astimezone(pytz.utc)
                else: # Si es solo fecha
                    task_data['due_date'] = pytz.utc.localize(datetime(due.dt.year, due.dt.month, due.dt.day, 23, 59, 59))
            
            # STATUS
            status_ical = str(ical_todo.get('status', '')).upper()
            task_data['is_completed'] = (status_ical == 'COMPLETED')

            # UID
            task_data['id'] = str(ical_todo.get('uid', uuid.uuid4()))

            break # Solo procesamos el primer VTODO
    
    return task_data

@router.get("/caldav/principals/{account_id}/")
async def get_caldav_principal(account_id: str, request: Request):
    """
    Endpoint para que los clientes CalDAV descubran las URLs de las colecciones de calendarios.
    """
    # En una implementación real, esto devolvería información sobre el principal
    # y enlaces a las colecciones de calendarios.
    # Por ahora, simplemente devolvemos una respuesta WebDAV básica.
    response = Response(content="", media_type="text/xml")
    response.headers["DAV"] = "1, 2, calendar-access"
    response.headers["Allow"] = "OPTIONS, GET, HEAD, POST, PUT, DELETE, TRACE, COPY, MOVE"
    return response

@router.get("/caldav/calendars/{account_id}/default/")
async def get_caldav_calendar_collection(account_id: str, request: Request):
    """
    Endpoint para que los clientes CalDAV descubran las propiedades del calendario
    y los eventos contenidos.
    """
    # Similar al principal, esto es una respuesta placeholder.
    # En una implementación real, se devolvería una lista de eventos.
    response = Response(content="", media_type="text/xml")
    response.headers["DAV"] = "1, 2, calendar-access"
    response.headers["Allow"] = "OPTIONS, GET, HEAD, POST, PUT, DELETE, TRACE, COPY, MOVE, PROPFIND, REPORT"
    return response

from core.agenda_manager import get_event_by_id_db, update_event_db, schedule_event, cancel_event # Importar funciones para eventos
from core.agenda_manager import get_task_by_id_db, update_task_db # Importar funciones para tareas
from core.tasks_manager import create_task, delete_task # Importar funciones para crear y eliminar tareas

@router.get("/caldav/calendars/{account_id}/default/{uid}.ics")
async def get_caldav_resource(
    account_id: str,
    uid: str,
    request: Request,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Recupera un evento o tarea específica en formato iCalendar.
    """
    if account_id != current_account_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso no autorizado.")
    
    # Intentar buscar como evento
    resource = await get_event_by_id_db(current_account_id, int(uid))
    resource_type = "event"

    if not resource:
        # Si no es un evento, intentar buscar como tarea
        resource = await get_task_by_id_db(current_account_id, int(uid))
        resource_type = "task"
    
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurso no encontrado.")
    
    account = await db.get(Account, uuid.UUID(current_account_id))
    if not account or not account.timezone:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo determinar la zona horaria del usuario.")

    if resource_type == "event":
        ical_content = _event_to_ical(resource, account.timezone)
    else: # resource_type == "task"
        ical_content = _task_to_ical(resource, account.timezone)
    
    return Response(content=ical_content, media_type="text/calendar")

@router.put("/caldav/calendars/{account_id}/default/{uid}.ics")
async def put_caldav_resource(
    account_id: str,
    uid: str,
    request: Request,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Crea o actualiza un evento o tarea en formato iCalendar.
    """
    if account_id != current_account_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso no autorizado.")
    
    ical_data = await request.body()
    
    # Determinar si es VEVENT o VTODO
    if b"VEVENT" in ical_data:
        resource_type = "event"
        try:
            data = await _ical_to_event_data(ical_data, current_account_id, db)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Error al parsear iCalendar (VEVENT): {e}")
        
        # Lógica para crear/actualizar evento
        existing_event = await get_event_by_id_db(current_account_id, int(uid))
        if existing_event:
            # Verificar el If-Match ETag para evitar sobrescrituras accidentales
            if_match = request.headers.get("If-Match")
            if existing_event.etag and if_match and existing_event.etag != if_match:
                raise HTTPException(status_code=status.HTTP_412_PRECONDITION_FAILED, detail="ETag no coincide.")

            updated_instance = await update_event_db(
                db_session=db,
                account_id=current_account_id,
                event_id=int(uid), # El UID de CalDAV se mapea a nuestro ID
                summary=data.get('summary'),
                description=data.get('description'),
                location=data.get('location'),
                event_datetime_utc=data.get('event_datetime_utc'),
                duration_minutes=data.get('duration_minutes'),
                attendee_ids=data.get('attendee_ids'),
                external_attendees=data.get('external_attendees'),
            )
            if not updated_instance:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al actualizar el evento.")
            
            # Generar y guardar un nuevo ETag
            new_etag = str(uuid.uuid4())
            updated_instance.etag = new_etag
            await db.commit()
            await db.refresh(updated_instance)
            return Response(status_code=status.HTTP_200_OK, headers={"ETag": new_etag})
        else:
            # Si no existe, crearlo. El UID de CalDAV se usará como ID de la DB si es un entero válido
            event_id_to_use = int(uid) if uid.isdigit() else None
            if event_id_to_use is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="UID de evento inválido para creación.")

            # Verificar el If-None-Match para creación (debe ser *)
            if_none_match = request.headers.get("If-None-Match")
            if if_none_match and if_none_match != "*":
                raise HTTPException(status_code=status.HTTP_412_PRECONDITION_FAILED, detail="If-None-Match inválido para creación.")
            if existing_event: # Si ya existe, es un conflicto
                raise HTTPException(status_code=status.HTTP_412_PRECONDITION_FAILED, detail="El recurso ya existe.")


            success, message, new_instance = await schedule_event(
                account_id=current_account_id,
                summary=data.get('summary', 'Evento CalDAV'),
                description=data.get('description'),
                location=data.get('location'),
                event_date=data['event_datetime_utc'].strftime('%Y-%m-%d'),
                event_time=data['event_datetime_utc'].strftime('%H:%M'),
                duration_minutes=data.get('duration_minutes'),
                attendee_ids=data.get('attendee_ids'),
                external_attendees=data.get('external_attendees'),
                event_id=event_id_to_use # Pasar el UID como event_id
            )
            if not success or not new_instance:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message or "Error desconocido al crear el evento.")
            
            # Asignar ETag al nuevo evento
            new_etag = str(uuid.uuid4())
            new_instance.etag = new_etag
            await db.commit()
            await db.refresh(new_instance)
            return Response(status_code=status.HTTP_201_CREATED, headers={"ETag": new_etag})

    elif b"VTODO" in ical_data:
        resource_type = "task"
        try:
            data = await _ical_to_task_data(ical_data, current_account_id, db)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Error al parsear iCalendar (VTODO): {e}")
        
        # Lógica para crear/actualizar tarea
        existing_task = await get_task_by_id_db(current_account_id, int(uid))
        if existing_task:
            # Verificar el If-Match ETag para evitar sobrescrituras accidentales
            if_match = request.headers.get("If-Match")
            if existing_task.etag and if_match and existing_task.etag != if_match:
                raise HTTPException(status_code=status.HTTP_412_PRECONDITION_FAILED, detail="ETag no coincide.")

            updated_instance = await update_task_db(
                db_session=db,
                account_id=current_account_id,
                task_id=int(uid), # El UID de CalDAV se mapea a nuestro ID
                summary=data.get('summary'),
                description=data.get('description'),
                due_date=data.get('due_date'),
                is_completed=data.get('is_completed'),
            )
            if not updated_instance:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al actualizar la tarea.")
            
            # Generar y guardar un nuevo ETag
            new_etag = str(uuid.uuid4())
            updated_instance.etag = new_etag
            await db.commit()
            await db.refresh(updated_instance)
            return Response(status_code=status.HTTP_200_OK, headers={"ETag": new_etag})
        else:
            # Crear nueva tarea. El UID de CalDAV se usará como ID de la DB si es un entero válido
            task_id_to_use = int(uid) if uid.isdigit() else None
            if task_id_to_use is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="UID de tarea inválido para creación.")

            # Verificar el If-None-Match para creación (debe ser *)
            if_none_match = request.headers.get("If-None-Match")
            if if_none_match and if_none_match != "*":
                raise HTTPException(status_code=status.HTTP_412_PRECONDITION_FAILED, detail="If-None-Match inválido para creación.")
            
            # Si ya existe, es un conflicto (aunque ya lo comprobamos arriba con existing_task)
            if existing_task:
                 raise HTTPException(status_code=status.HTTP_412_PRECONDITION_FAILED, detail="El recurso ya existe.")

            from core.tasks_manager import create_task
            success, message, new_instance = await create_task(
                account_id=current_account_id,
                description=data.get('description', 'Tarea CalDAV'),
                due_date=data.get('due_date'),
                is_completed=data.get('is_completed', False),
                task_id=task_id_to_use # Pasar el UID como task_id
            )
            if not success or not new_instance:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message or "Error desconocido al crear la tarea.")
            
            # Generar y guardar un nuevo ETag
            new_etag = str(uuid.uuid4())
            new_instance.etag = new_etag
            await db.commit()
            await db.refresh(new_instance)
            return Response(status_code=status.HTTP_201_CREATED, headers={"ETag": new_etag})
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo de iCalendar no soportado (solo VEVENT y VTODO).")

@router.delete("/caldav/calendars/{account_id}/default/{uid}.ics")
async def delete_caldav_resource(
    account_id: str,
    uid: str,
    request: Request,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Elimina un evento o tarea.
    """
    if account_id != current_account_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso no autorizado.")
    
    # Intentar buscar el recurso para verificar el ETag
    resource = await get_event_by_id_db(current_account_id, int(uid))
    resource_type = "event"

    if not resource:
        resource = await get_task_by_id_db(current_account_id, int(uid))
        resource_type = "task"
    
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurso no encontrado.")

    # Verificar el If-Match ETag para evitar eliminaciones accidentales
    if_match = request.headers.get("If-Match")
    if resource.etag and if_match and resource.etag != if_match:
        raise HTTPException(status_code=status.HTTP_412_PRECONDITION_FAILED, detail="ETag no coincide.")

    if resource_type == "event":
        from core.agenda_manager import cancel_event # Importar función
        success, message = await cancel_event(current_account_id, int(uid))
    else: # resource_type == "task"
        from core.tasks_manager import delete_task # Importar función para eliminar tareas
        success, message = await delete_task(current_account_id, int(uid))
    
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message or "Recurso no encontrado o no se pudo eliminar.")
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)
    
    import xml.etree.ElementTree as ET
    from xml.dom import minidom
    
    # Helper para XML
    def _pretty_print_xml(elem: ET.Element) -> str:
        """Retorna una cadena XML con formato legible."""
        rough_string = ET.tostring(elem, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")
    
    @router.propfind("/caldav/calendars/{account_id}/default/", status_code=207)
    async def propfind_caldav_calendar_collection(
        account_id: str,
        request: Request,
        current_account_id: str = Depends(get_current_account_id),
        db: AsyncSession = Depends(get_db_session)
    ):
        """
        Endpoint PROPFIND para que los clientes CalDAV descubran las propiedades del calendario
        y los recursos (eventos/tareas) contenidos.
        """
        if account_id != current_account_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso no autorizado.")
    
        # Lógica para construir la respuesta XML
        multistatus = ET.Element("{DAV:}multistatus",
                                 namespaces={
                                     'D': "DAV:",
                                     'C': "urn:ietf:params:xml:ns:caldav"
                                 })
    
        # Propiedades de la colección de calendario
        response_elem = ET.SubElement(multistatus, "{DAV:}response")
        href = ET.SubElement(response_elem, "{DAV:}href")
        href.text = f"/caldav/calendars/{account_id}/default/"
    
        propstat = ET.SubElement(response_elem, "{DAV:}propstat")
        prop = ET.SubElement(propstat, "{DAV:}prop")
    
        # Propiedades requeridas por CalDAV
        ET.SubElement(prop, "{DAV:}resourcetype").append(ET.Element("{DAV:}collection"))
        ET.SubElement(prop, "{DAV:}resourcetype").append(ET.Element("{C:}calendar"))
        ET.SubElement(prop, "{DAV:}displayname").text = f"Calendario de {account_id}"
        ET.SubElement(prop, "{C:}calendar-description").text = "Calendario principal de KognitoAI"
        ET.SubElement(prop, "{C:}supported-calendar-component-set").text = """
            <C:comp name="VEVENT"/>
            <C:comp name="VTODO"/>
        """
    
        ET.SubElement(propstat, "{DAV:}status").text = "HTTP/1.1 200 OK"
    
        # Obtener eventos y tareas para listarlos como recursos
        from core.agenda_manager import get_events_as_dicts
        from core.tasks_manager import get_tasks_as_dicts # Asumiendo una función similar para tareas
    
        events = await get_events_as_dicts(current_account_id)
        tasks = await get_tasks_as_dicts(current_account_id) # Obtener tareas
    
        # Añadir eventos como recursos
        for event in events:
            event_response_elem = ET.SubElement(multistatus, "{DAV:}response")
            event_href = ET.SubElement(event_response_elem, "{DAV:}href")
            event_href.text = f"/caldav/calendars/{account_id}/default/{event['id']}.ics"
            event_propstat = ET.SubElement(event_response_elem, "{DAV:}propstat")
            event_prop = ET.SubElement(event_propstat, "{DAV:}prop")
            ET.SubElement(event_prop, "{DAV:}resourcetype").append(ET.Element("{C:}calendar-object"))
            ET.SubElement(event_prop, "{DAV:}getetag").text = event['etag'] if event['etag'] else str(uuid.uuid4()) # Usar ETag persistente
            ET.SubElement(event_propstat, "{DAV:}status").text = "HTTP/1.1 200 OK"
        
        # Añadir tareas como recursos
        for task in tasks:
            task_response_elem = ET.SubElement(multistatus, "{DAV:}response")
            task_href = ET.SubElement(task_response_elem, "{DAV:}href")
            task_href.text = f"/caldav/calendars/{account_id}/default/{task['id']}.ics"
            task_propstat = ET.SubElement(task_response_elem, "{DAV:}propstat")
            task_prop = ET.SubElement(task_propstat, "{DAV:}prop")
            ET.SubElement(task_prop, "{DAV:}resourcetype").append(ET.Element("{C:}calendar-object"))
            ET.SubElement(task_prop, "{DAV:}getetag").text = task['etag'] if task['etag'] else str(uuid.uuid4()) # Usar ETag persistente
            ET.SubElement(task_propstat, "{DAV:}status").text = "HTTP/1.1 200 OK"
    
        return Response(content=_pretty_print_xml(multistatus), media_type="application/xml")

@router.report("/caldav/calendars/{account_id}/default/", status_code=207)
async def report_caldav_calendar_collection(
    account_id: str,
    request: Request,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Endpoint REPORT para que los clientes CalDAV realicen consultas avanzadas.
    Soporta principalmente calendar-query para rangos de tiempo.
    """
    if account_id != current_account_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso no autorizado.")

    request_body = await request.body()
    root = ET.fromstring(request_body)

    # Namespaces
    DAV_NS = "DAV:"
    CALDAV_NS = "urn:ietf:params:xml:ns:caldav"
    
    # Buscar el filtro de rango de tiempo (calendar-query)
    time_range_filter = root.find(f".//{{{CALDAV_NS}}}time-range")
    start_time_str = None
    end_time_str = None

    if time_range_filter is not None:
        start_time_str = time_range_filter.get("start")
        end_time_str = time_range_filter.get("end")

    start_time_utc = None
    end_time_utc = None

    if start_time_str:
        start_time_utc = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
    if end_time_str:
        end_time_utc = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))

    multistatus = ET.Element(f"{{{DAV_NS}}}multistatus",
                             namespaces={
                                 'D': DAV_NS,
                                 'C': CALDAV_NS
                             })
    
    # Obtener la zona horaria del usuario para _event_to_ical y _task_to_ical
    account = await db.get(Account, uuid.UUID(current_account_id))
    if not account or not account.timezone:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo determinar la zona horaria del usuario.")

    # Consulta de eventos
    from core.agenda_manager import get_events_as_dicts
    events = await get_events_as_dicts(current_account_id, include_past=True) # Incluir pasados para REPORT

    for event in events:
        # Convertir a datetime con zona horaria para comparación
        event_dt_utc = datetime.fromisoformat(event['event_datetime_utc'].replace("Z", "+00:00"))
        if (not start_time_utc or event_dt_utc >= start_time_utc) and \
           (not end_time_utc or event_dt_utc <= end_time_utc):
            
            response_elem = ET.SubElement(multistatus, f"{{{DAV_NS}}}response")
            href = ET.SubElement(response_elem, f"{{{DAV_NS}}}href")
            href.text = f"/caldav/calendars/{account_id}/default/{event['id']}.ics"
            
            propstat = ET.SubElement(response_elem, f"{{{DAV_NS}}}propstat")
            prop = ET.SubElement(propstat, f"{{{DAV_NS}}}prop")
            
            # Devolver el iCalendar completo para el evento
            caldata = ET.SubElement(prop, f"{{{CALDAV_NS}}}calendar-data")
            # Recrear el objeto AgendaEvent para pasarlo a _event_to_ical
            agenda_event_obj = AgendaEvent(
                id=event['id'],
                account_id=uuid.UUID(event['account_id']),
                summary=event['summary'],
                description=event['description'],
                location=event['location'],
                event_datetime_utc=event_dt_utc,
                is_active=event['is_active'],
                etag=event['etag'] # Incluir el ETag
            )
            caldata.text = _event_to_ical(agenda_event_obj, account.timezone)
            ET.SubElement(propstat, f"{{{DAV_NS}}}status").text = "HTTP/1.1 200 OK"

    # Consulta de tareas
    from core.tasks_manager import get_tasks_as_dicts
    tasks = await get_tasks_as_dicts(current_account_id, include_completed=True) # Incluir completadas para REPORT

    for task in tasks:
        # Asumiendo que due_date es el campo relevante para el rango de tiempo
        if task['due_date']:
            task_dt_utc = datetime.fromisoformat(task['due_date'].replace("Z", "+00:00"))
            if (not start_time_utc or task_dt_utc >= start_time_utc) and \
               (not end_time_utc or task_dt_utc <= end_time_utc):
                
                response_elem = ET.SubElement(multistatus, f"{{{DAV_NS}}}response")
                href = ET.SubElement(response_elem, f"{{{DAV_NS}}}href")
                href.text = f"/caldav/calendars/{account_id}/default/{task['id']}.ics"
                
                propstat = ET.SubElement(response_elem, f"{{{DAV_NS}}}propstat")
                prop = ET.SubElement(propstat, f"{{{DAV_NS}}}prop")
                
                # Devolver el iCalendar completo para la tarea
                caldata = ET.SubElement(prop, f"{{{CALDAV_NS}}}calendar-data")
                # Recrear el objeto Task para pasarlo a _task_to_ical
                task_obj = Task(
                    id=task['id'],
                    account_id=uuid.UUID(task['account_id']),
                    description=task['description'],
                    due_date=task_dt_utc,
                    is_completed=task['is_completed'],
                    etag=task['etag'] # Incluir el ETag
                )
                caldata.text = _task_to_ical(task_obj, account.timezone)
                ET.SubElement(propstat, f"{{{DAV_NS}}}status").text = "HTTP/1.1 200 OK"

    return Response(content=_pretty_print_xml(multistatus), media_type="application/xml")