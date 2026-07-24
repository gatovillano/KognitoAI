import uuid
from core.llm_manager import get_fast_llm, get_main_llm, get_llm_for_user
from langchain_core.prompts import ChatPromptTemplate

async def summarize_email_body(body_text: str, account_id: uuid.UUID = None) -> str:
    llm = None
    if account_id:
        try:
            llm = await get_llm_for_user(str(account_id), purpose="fast")
        except Exception:
            pass
    if not llm:
        llm = get_fast_llm() or get_main_llm()
        
    if not llm:
        return "Servicio de IA no disponible en este momento."

    prompt = ChatPromptTemplate.from_messages([
        ("system", "Eres K Kai, un asistente de IA. Tu tarea es resumir el siguiente correo electrónico de manera concisa. Devuelve el resumen en español, estructurado con viñetas claras (markdown) y destaca los puntos de acción o compromisos si los hay."),
        ("user", "Cuerpo del correo:\n\n{body_text}")
    ])
    
    chain = prompt | llm
    try:
        response = await chain.ainvoke({"body_text": body_text})
        return response.content
    except Exception as e:
        return f"Error al generar el resumen: {str(e)}"

async def draft_email_response(instructions: str, original_body: str = None, original_subject: str = None, account_id: uuid.UUID = None) -> str:
    llm = None
    if account_id:
        try:
            llm = await get_llm_for_user(str(account_id), purpose="main")
        except Exception:
            pass
    if not llm:
        llm = get_main_llm() or get_fast_llm()
        
    if not llm:
        return "Servicio de IA no disponible en este momento."

    system_prompt = (
        "Eres K Kai, un redactor de correos inteligente integrado en KognitoAI. "
        "Genera el texto de un correo electrónico en base a las instrucciones del usuario. "
        "Si se provee el correo original al que se responde, utilízalo como contexto histórico. "
        "Devuelve únicamente el cuerpo del correo redactado, listo para ser enviado."
    )
    
    user_prompt = f"Instrucciones de redacción: {instructions}\n\n"
    if original_body:
        user_prompt += f"Asunto original: {original_subject}\nCuerpo original:\n{original_body}"
        
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "{user_prompt}")
    ])
    
    chain = prompt | llm
    try:
        response = await chain.ainvoke({"user_prompt": user_prompt})
        return response.content
    except Exception as e:
        return f"Error al generar el borrador: {str(e)}"
