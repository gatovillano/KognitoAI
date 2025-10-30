import logging
from fastapi import APIRouter, HTTPException, Depends, status, Response
from pydantic import BaseModel, Field, computed_field, field_serializer

logger = logging.getLogger(__name__)
from typing import List, Optional, Any, Literal, Union, Dict
import uuid
from datetime import datetime
import os
from fpdf import FPDF, fpdf
import io

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from core.database import get_db_session, Form as DBForm, ContactProfile as DBContactProfile, Account, FormResponse as DBFormResponse
from api.contact_profiles import ContactProfileResponse
from utils.security import get_current_active_account, get_optional_current_active_account

router = APIRouter()

# --- Models ---

class FormField(BaseModel):
    id: str
    label: str
    description: Optional[str] = None
    type: Literal['text', 'checkbox', 'textarea', 'select', 'radio']
    options: Optional[List[str]] = None
    is_required: bool = False

class FormSection(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    elements: List['FormElement'] = []

FormElement = Union[FormField, FormSection]

FormSection.update_forward_refs()

class FormBase(BaseModel):
    name: str = Field(..., validation_alias='title')
    description: Optional[str] = None
    is_public: bool = False


class FormCreate(FormBase):
    elements: List[FormElement] = []


class FormUpdate(FormBase):
    elements: List[FormElement] = []

def _deserialize_form_elements_recursively(elements_data: List[Dict[str, Any]]) -> List[FormElement]:
    deserialized_elements = []
    for element_data in elements_data:
        if "type" in element_data: # Es un FormField
            deserialized_elements.append(FormField(**element_data))
        elif "elements" in element_data: # Es un FormSection
            # Deserializar recursivamente los elementos de la sección
            element_data['elements'] = _deserialize_form_elements_recursively(element_data['elements'])
            deserialized_elements.append(FormSection(**element_data))
        # else: # Manejar otros tipos si es necesario
    return deserialized_elements

class FormInDB(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    form_schema: List[Dict[str, Any]] = Field(..., alias='schema')
    is_public: bool

    @computed_field
    @property
    def title(self) -> str:
        return self.name

    @computed_field
    @property
    def elements(self) -> List[FormElement]:
        # Asumiendo que self.schema contiene los datos serializados del DBForm
        return _deserialize_form_elements_recursively(self.form_schema)

    @computed_field
    @property
    def shareable_link(self) -> str:
        return f"/forms/fill/{self.id}"

    class Config:
        from_attributes = True

class FormResponseAnswer(BaseModel):
    field_id: str
    value: Any

class FormResponseCreate(BaseModel):
    form_id: uuid.UUID
    answers: List[FormResponseAnswer]
    contact_profile_id: Optional[uuid.UUID] = None

class FormResponse(BaseModel):
    id: uuid.UUID
    form_id: uuid.UUID
    account_id: Optional[uuid.UUID] = None
    contact_profile_id: Optional[uuid.UUID] = None
    answers: List[Dict[str, Any]]
    submitted_at: datetime

    class Config:
        from_attributes = True

class ProfileLinkRequest(BaseModel):
    profile_id: str

def _serialize_form_elements_recursively(elements: List[FormElement]) -> List[Dict[str, Any]]:
    serialized_elements = []
    for element in elements:
        # Si el elemento ya es un diccionario, lo usamos directamente
        if isinstance(element, dict):
            serialized_elements.append(element)
        elif isinstance(element, FormSection):
            # Si es una sección, serializar sus elementos recursivamente
            serialized_section = element.model_dump()
            serialized_section['elements'] = _serialize_form_elements_recursively(element.elements)
            serialized_elements.append(serialized_section)
        else:
            # Si es un campo (FormField), simplemente serializarlo
            serialized_elements.append(element.model_dump())
    return serialized_elements

# --- Endpoints ---

@router.post("/forms", response_model=FormInDB, status_code=status.HTTP_201_CREATED, tags=["Forms"])
async def create_form(
    form_create: FormCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: Account = Depends(get_current_active_account)
):
    """
    Create a new form.
    """
    logger.info(f"Received request to create form: {form_create.name} for account {current_user.id}")

    db_form = DBForm(
        account_id=current_user.id,
        name=form_create.name, # Usar name como el nombre del formulario
        description=form_create.description,
        is_public=form_create.is_public,
        schema=_serialize_form_elements_recursively(form_create.elements)
    )
    db.add(db_form)
    await db.commit()
    await db.refresh(db_form)
    return db_form

@router.get("/forms", response_model=List[FormInDB], tags=["Forms"])
async def get_forms(
    db: AsyncSession = Depends(get_db_session),
    current_user: Account = Depends(get_current_active_account)
):
    """
    Get a list of all forms for the current user.
    """
    result = await db.execute(
        select(DBForm).where(DBForm.account_id == current_user.id)
    )
    forms = result.scalars().all()
    return forms

@router.get("/forms/{form_id}", response_model=FormInDB, tags=["Forms"])
async def get_form(
    form_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: Optional[Account] = Depends(get_optional_current_active_account)
):
    """
    Get the details of a specific form.
    """
    form = await db.get(DBForm, form_id)

    if not form:
        raise HTTPException(status_code=404, detail="Form not found")

    # Check if the form is public
    if form.is_public:
        return form

    # If the form is not public, a user must be authenticated
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    # If the user is authenticated, check if they are the owner
    if str(form.account_id) != str(current_user.id):
        raise HTTPException(status_code=404, detail="Form not found")

    return form

@router.put("/forms/{form_id}", response_model=FormInDB, tags=["Forms"])
async def update_form(
    form_id: uuid.UUID,
    form_update: FormUpdate,
    db: AsyncSession = Depends(get_db_session),
    current_user: Account = Depends(get_current_active_account)
):
    """
    Update an existing form.
    """
    form = await db.get(DBForm, form_id)
    if not form or str(form.account_id) != str(current_user.id):
        raise HTTPException(status_code=404, detail="Form not found")
    
    form.name = form_update.name
    form.description = form_update.description
    form.is_public = form_update.is_public
    form.schema = _serialize_form_elements_recursively(form_update.elements)
    # The updated_at column is automatically updated by the database trigger (onupdate=text("CURRENT_TIMESTAMP"))
    # No need to manually set form.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(form)
    return form

@router.delete("/forms/{form_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Forms"])
async def delete_form(
    form_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: Account = Depends(get_current_active_account)
):
    """
    Delete a form.
    """
    form = await db.get(DBForm, form_id)
    if not form or str(form.account_id) != str(current_user.id):
        raise HTTPException(status_code=404, detail="Form not found")
    
    await db.delete(form)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/forms/{form_id}/responses", response_model=FormResponse, tags=["Form Responses"])
async def create_form_response(
    form_id: uuid.UUID,
    response_data: FormResponseCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: Optional[Account] = Depends(get_optional_current_active_account)
):
    """
    Submit a new response for a form.
    """
    form = await db.get(DBForm, form_id)
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")

    if not form.is_public:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required to submit a response to this form")
        if str(form.account_id) != str(current_user.id):
            # Allow submitting to forms owned by other users if it is not public?
            # For now, only owner can submit to non-public forms.
            raise HTTPException(status_code=403, detail="You do not have permission to submit a response to this form")

    # Serializar las respuestas a una lista de diccionarios para la base de datos
    serialized_answers = [answer.model_dump() for answer in response_data.answers]

    db_form_response = DBFormResponse(
        id=uuid.uuid4(),
        form_id=form_id,
        account_id=form.account_id, # Usar el ID de la cuenta del propietario del formulario
        contact_profile_id=response_data.contact_profile_id,
        answers=serialized_answers
    )
    db.add(db_form_response)
    await db.commit()
    await db.refresh(db_form_response)
    return db_form_response


@router.get("/forms/{form_id}/responses", response_model=List[FormResponse], tags=["Form Responses"])
async def get_form_responses(
    form_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: Account = Depends(get_current_active_account)
):
    """
    Get all responses for a specific form.
    """
    # Primero, verifica que el usuario actual es el propietario del formulario
    form = await db.get(DBForm, form_id)
    if not form or str(form.account_id) != str(current_user.id):
        raise HTTPException(status_code=404, detail="Form not found or you do not have permission to view its responses")

    result = await db.execute(
        select(DBFormResponse).where(DBFormResponse.form_id == form_id)
    )
    responses = result.scalars().all()
    return responses

@router.post("/forms/{form_id}/link-profile", tags=["Forms"])
async def link_profile_to_form(
    form_id: uuid.UUID,
    request: ProfileLinkRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Vincula un perfil de contacto a un formulario.
    """
    form = await db.get(DBForm, form_id)
    if not form:
        raise HTTPException(status_code=404, detail="Formulario no encontrado")

    profile = await db.get(DBContactProfile, uuid.UUID(request.profile_id))
    if not profile:
        raise HTTPException(status_code=404, detail="Perfil de contacto no encontrado")

    if profile not in form.contact_profiles:
        form.contact_profiles.append(profile)
        await db.commit()
        await db.refresh(form)
    return {"message": "Perfil vinculado exitosamente"}

@router.post("/forms/{form_id}/unlink-profile", tags=["Forms"])
async def unlink_profile_from_form(
    form_id: uuid.UUID,
    request: ProfileLinkRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Desvincula un perfil de contacto de un formulario.
    """
    form = await db.get(DBForm, form_id)
    if not form:
        raise HTTPException(status_code=404, detail="Formulario no encontrado")

    profile = await db.get(DBContactProfile, uuid.UUID(request.profile_id))
    if not profile:
        raise HTTPException(status_code=404, detail="Perfil de contacto no encontrado")

    if profile in form.contact_profiles:
        form.contact_profiles.remove(profile)
        await db.commit()
        await db.refresh(form)
    return {"message": "Perfil desvinculado exitosamente"}

@router.get("/forms/{form_id}/linked-profiles", response_model=List[ContactProfileResponse], tags=["Forms"])
async def get_linked_profiles(
    form_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Obtiene la lista de perfiles de contacto vinculados a un formulario.
    """
    form_result = await db.execute(
        select(DBForm).where(DBForm.id == form_id).options(selectinload(DBForm.contact_profiles))
    )
    form = form_result.scalars().first()

    if not form:
        raise HTTPException(status_code=404, detail="Formulario no encontrado")
    
    # Convertir los modelos SQLAlchemy a modelos Pydantic
    linked_profiles_pydantic = [ContactProfileResponse.from_orm(profile) for profile in form.contact_profiles]
    return linked_profiles_pydantic

@router.get("/form-responses/{form_response_id}/linked-profiles", response_model=List[ContactProfileResponse], tags=["Form Responses"])
async def get_linked_profiles_for_form_response(
    form_response_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: Account = Depends(get_current_active_account)
):
    """
    Obtiene la lista de perfiles de contacto vinculados a una respuesta de formulario.
    """
    form_response = await db.get(DBFormResponse, form_response_id)

    if not form_response or str(form_response.account_id) != str(current_user.id):
        raise HTTPException(status_code=404, detail="Respuesta de formulario no encontrada o no autorizada.")

    if form_response.contact_profile_id:
        profile = await db.get(DBContactProfile, form_response.contact_profile_id)
        if profile:
            return [ContactProfileResponse.from_orm(profile)]
    return []

@router.delete("/form-responses/{response_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Form Responses"])
async def delete_form_response(
    response_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: Account = Depends(get_current_active_account)
):
    """
    Delete a specific form response.
    """
    # First, get the response
    response = await db.get(DBFormResponse, response_id)
    if not response:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response not found")

    # Now, get the form to check ownership
    form = await db.get(DBForm, response.form_id)
    if not form:
        # This case is unlikely if the response exists, but good for data integrity
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated form not found")

    # Check if the current user owns the form
    if str(form.account_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to delete this response")

    # If all checks pass, delete the response
    await db.delete(response)
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get("/form-responses/{response_id}/pdf", tags=["Form Responses"])
async def get_form_response_pdf(
    response_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: Account = Depends(get_current_active_account)
):
    """
    Generates a PDF for a specific form response.
    """
    form_response = await db.get(DBFormResponse, response_id)
    if not form_response:
        raise HTTPException(status_code=404, detail="Form response not found")

    form = await db.get(DBForm, form_response.form_id)
    if not form or str(form.account_id) != str(current_user.id):
        raise HTTPException(status_code=404, detail="Form not found or unauthorized")

    pdf = FPDF(font_cache_dir=".")
    pdf.add_page()
    # Add a Unicode font (e.g., DejaVuSans)
    # FPDF will download it if not present in the cache directory
    pdf.add_font("DejaVu", "", os.path.join(os.path.dirname(__file__), "fonts", "DejaVuSansCondensed.ttf"), uni=True)
    pdf.set_font("DejaVu", size=16)
    pdf.cell(200, 10, txt=f"Respuesta del Formulario: {form.name}", ln=True, align="C")
    pdf.set_font("DejaVu", size=12)
    pdf.cell(200, 10, txt=f"Enviado el: {form_response.submitted_at.strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="L")
    pdf.ln(10)

    # Extract all fields from the form schema to map field_id to label
    field_map = {}
    def extract_fields(elements):
        for element in elements:
            if "type" in element: # It's a FormField
                field_map[element["id"]] = element["label"]
            elif "elements" in element: # It's a FormSection
                extract_fields(element["elements"])
    extract_fields(form.schema)

    for answer in form_response.answers:
        field_label = field_map.get(answer["field_id"], answer["field_id"])
        pdf.set_font("DejaVu", "B", size=12)
        pdf.multi_cell(pdf.w - 2 * pdf.l_margin, 10, txt=f"Pregunta: {field_label}")
        pdf.set_font("DejaVu", size=12)
        answer_value = answer["value"]
        if isinstance(answer_value, list):
            answer_value = ", ".join(map(str, answer_value))
        pdf.multi_cell(pdf.w - 2 * pdf.l_margin, 10, txt=f"Respuesta: {answer_value}")
        pdf.ln(5)

    pdf_output = pdf.output(dest='S').encode('utf-8') # Output as string, then encode to bytes
    return Response(content=pdf_output, media_type="application/pdf", headers={
        "Content-Disposition": f"attachment; filename='form_response_{response_id}.pdf'"
    })

@router.get("/forms/{form_id}/responses/pdf", tags=["Form Responses"])
async def get_form_responses_pdf_report(
    form_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: Account = Depends(get_current_active_account)
):
    """
    Generates a PDF report for all responses of a specific form.
    """
    form = await db.get(DBForm, form_id)
    if not form or str(form.account_id) != str(current_user.id):
        raise HTTPException(status_code=404, detail="Form not found or unauthorized")

    result = await db.execute(
        select(DBFormResponse).where(DBFormResponse.form_id == form_id)
    )
    form_responses = result.scalars().all()

    pdf = FPDF(font_cache_dir=".")
    pdf.add_page()
    pdf.add_font("DejaVu", "", os.path.join(os.path.dirname(__file__), "fonts", "DejaVuSansCondensed.ttf"), uni=True)
    pdf.set_font("DejaVu", size=16)
    pdf.cell(200, 10, txt=f"Reporte de Respuestas para: {form.name}", ln=True, align="C")
    pdf.ln(10)

    field_map = {}
    def extract_fields(elements):
        for element in elements:
            if "type" in element: # It's a FormField
                field_map[element["id"]] = element["label"]
            elif "elements" in element: # It's a FormSection
                extract_fields(element["elements"])
    extract_fields(form.schema)

    if not form_responses:
        pdf.set_font("DejaVu", size=12)
        pdf.cell(200, 10, txt="No hay respuestas para este formulario.", ln=True, align="C")
    else:
        for i, form_response in enumerate(form_responses):
            if i > 0:
                pdf.add_page() # New page for each response in the report
            pdf.set_font("DejaVu", "B", size=14)
            pdf.cell(200, 10, txt=f"Respuesta #{i+1} (ID: {str(form_response.id)[:8]}...)", ln=True, align="L")
            pdf.set_font("DejaVu", size=12)
            pdf.cell(200, 10, txt=f"Enviado el: {form_response.submitted_at.strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="L")
            pdf.ln(5)

            for answer in form_response.answers:
                field_label = field_map.get(answer["field_id"], answer["field_id"])
                pdf.set_font("DejaVu", "B", size=12)
                pdf.multi_cell(pdf.w - 2 * pdf.l_margin, 10, txt=f"Pregunta: {field_label}")
                pdf.set_font("DejaVu", size=12)
                answer_value = answer["value"]
                if isinstance(answer_value, list):
                    answer_value = ", ".join(map(str, answer_value))
                pdf.multi_cell(pdf.w - 2 * pdf.l_margin, 10, txt=f"Respuesta: {answer_value}")
                pdf.ln(5)
            pdf.ln(10) # Add some space between responses if on the same page

    pdf_output = pdf.output(dest='S').encode('utf-8')
    return Response(content=pdf_output, media_type="application/pdf", headers={
        "Content-Disposition": f"attachment; filename='form_responses_report_{form_id}.pdf'"
    })