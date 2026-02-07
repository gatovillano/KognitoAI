import pyotp
import qrcode
import io
import base64
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from core.database import Account
from core.dependencies import get_db_session
from utils.security import get_current_account_id

router = APIRouter()

class MFAEnableResponse(BaseModel):
    secret: str
    qr_code: str

class MFAVerifyRequest(BaseModel):
    code: str

@router.post("/auth/mfa/enable", response_model=MFAEnableResponse, summary="Habilitar MFA")
async def enable_mfa(
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Genera un secreto TOTP y un código QR para habilitar MFA.
    El MFA no se activa hasta que se verifica el primer código.
    """
    # Obtener la cuenta
    account = await db.get(Account, current_account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    # Generar secreto
    secret = pyotp.random_base32()
    
    # Generar URI para QR
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=account.email or account.username or "Usuario",
        issuer_name="KognitoAI"
    )

    # Generar imagen QR
    qr = qrcode.make(totp_uri)
    img_byte_arr = io.BytesIO()
    qr.save(img_byte_arr, format='PNG')
    qr_base64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

    # Guardar secreto temporalmente (o podrías guardarlo en un estado 'pendiente')
    # Por simplicidad, lo guardamos pero no marcamos mfa_enabled como True aún
    account.mfa_secret = secret
    # account.mfa_enabled = False # Esto ya debería ser False por defecto o el estado actual
    
    await db.commit()

    return MFAEnableResponse(
        secret=secret,
        qr_code=f"data:image/png;base64,{qr_base64}"
    )

@router.post("/auth/mfa/verify", summary="Verificar y activar MFA")
async def verify_mfa(
    request: MFAVerifyRequest,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Verifica el código TOTP y activa MFA si es correcto.
    """
    account = await db.get(Account, current_account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    
    if not account.mfa_secret:
        raise HTTPException(status_code=400, detail="MFA no ha sido iniciado. Llama a /enable primero.")

    totp = pyotp.TOTP(account.mfa_secret)
    if totp.verify(request.code):
        account.mfa_enabled = True
        await db.commit()
        return {"message": "MFA activado exitosamente."}
    else:
        raise HTTPException(status_code=400, detail="Código inválido.")

@router.post("/auth/mfa/disable", summary="Desactivar MFA")
async def disable_mfa(
    request: MFAVerifyRequest, # Requerir código actual para desactivar por seguridad
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Desactiva MFA. Requiere un código válido actual.
    """
    account = await db.get(Account, current_account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    if not account.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA no está activado.")

    totp = pyotp.TOTP(account.mfa_secret)
    if totp.verify(request.code):
        account.mfa_enabled = False
        account.mfa_secret = None
        await db.commit()
        return {"message": "MFA desactivado."}
    else:
        raise HTTPException(status_code=400, detail="Código inválido. No se puede desactivar MFA.")