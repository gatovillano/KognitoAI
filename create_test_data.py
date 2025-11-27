import asyncio
import uuid
from datetime import datetime, timedelta
import pytz

from sqlalchemy.ext.asyncio import AsyncSession
from core.database import SessionLocal, Account, AgendaEvent, Task
from core.agenda_manager import schedule_event
from core.tasks_manager import create_task

from utils.db_session import DBSession

async def create_test_data():
    account_id_str = "test_user" # Usamos un string para el ID de cuenta de prueba
    account_uuid = uuid.UUID('00000000-0000-0000-0000-000000000001') # Un UUID fijo para el test_user

    async with DBSession(SessionLocal) as db:
        # 1. Crear o obtener la cuenta de prueba
        account = await db.get(Account, account_uuid)
        if not account:
            account = Account(
                id=account_uuid,
                username=account_id_str,
                email=f"{account_id_str}@example.com",
                timezone="America/Santiago" # Zona horaria de prueba
            )
            db.add(account)
            await db.commit()
            await db.refresh(account)
            print(f"Cuenta de prueba '{account_id_str}' creada con ID: {account.id}")
        else:
            print(f"Cuenta de prueba '{account_id_str}' ya existe con ID: {account.id}")
        
        # 2. Crear eventos de prueba
        now = datetime.now(pytz.utc)
        
        # Evento 1: En el futuro cercano
        event1_id = uuid.uuid4()
        success, message, event1 = await schedule_event(
            account_id=str(account.id),
            summary="Reunión de equipo CalDAV",
            event_date=(now + timedelta(days=1)).strftime('%Y-%m-%d'),
            event_time=(now + timedelta(days=1)).strftime('%H:%M'),
            description="Discutir el progreso del proyecto.",
            location="Sala de conferencias",
        )
        if success:
            print(f"Evento 1 creado: {event1.summary} (ID: {event1.id})")
        else:
            print(f"Error al crear Evento 1: {message}")

        # Evento 2: Con una zona horaria diferente (la API lo convertirá)
        event2_id = uuid.uuid4()
        # Simula un evento creado en "Europe/Berlin"
        berlin_tz = pytz.timezone("Europe/Berlin")
        event_time_berlin = (now + timedelta(days=2)).astimezone(berlin_tz)
        success, message, event2 = await schedule_event(
            account_id=str(account.id),
            summary="Conferencia internacional CalDAV",
            event_date=event_time_berlin.strftime('%Y-%m-%d'),
            event_time=event_time_berlin.strftime('%H:%M'),
            description="Presentación sobre nuevas tecnologías.",
            location="Online",
        )
        if success:
            print(f"Evento 2 creado: {event2.summary} (ID: {event2.id})")
        else:
            print(f"Error al crear Evento 2: {message}")

        # 3. Crear tareas de prueba
        # Tarea 1: Pendiente
        task1_id = uuid.uuid4()
        success, message, task1 = await create_task(
            account_id=str(account.id),
            description="Preparar informe mensual CalDAV",
            due_date=(now + timedelta(days=3)).astimezone(pytz.utc),
            is_completed=False,
        )
        if success:
            print(f"Tarea 1 creada: {task1.description} (ID: {task1.id})")
        else:
            print(f"Error al crear Tarea 1: {message}")
        
        # Tarea 2: Completada
        task2_id = uuid.uuid4()
        success, message, task2 = await create_task(
            account_id=str(account.id),
            description="Enviar correo a clientes CalDAV",
            due_date=(now - timedelta(days=1)).astimezone(pytz.utc), # Fecha pasada
            is_completed=True,
        )
        if success:
            print(f"Tarea 2 creada: {task2.description} (ID: {task2.id})")
        else:
            print(f"Error al crear Tarea 2: {message}")

if __name__ == "__main__":
    asyncio.run(create_test_data())