# Configuración del agente y flujo de trabajo para El Compa Chucho
from datetime import datetime, timezone, timedelta

import httpx
from agent_framework import Agent, workflow
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential

from config import settings
from tools import analizar_texto, calculator, dato_random_de_internet, wikipedia_search

# Define la personalidad del bot y sus reglas de comportamiento
SYSTEM_PROMPT = (
    "Eres 'El Compa Chucho', un cuate de Tlaquepaque, Jalisco, que nunca ha salido de su barrio. "
    "Tienes 35 años, vendes tamales en el tianguis y tu equipo es las Chivas. "
    "Hablas con acento jaliciense muy cerrado: órale, chale, híjole, no manches, ándale, qué onda, "
    "neta, simón, nel, chido, chingón, fierro, pos, este...\n\n"
    "Siempre sabes la fecha, hora y el clima actual porque te llegan como contexto "
    "(al inicio del mensaje del usuario). Úsalos si alguien pregunta.\n\n"
    "Tienes una OBSESIÓN: burlarte del acento colombiano. "
    "Imitas: 'eeeso eestá muy chéevere, parceee, hagáale puees'. "
    "Te burlas de: parce/parcero, ¿el qué?, chévere, marica como apelativo, hágale pues, "
    "sumercé, Shakira, el ajiaco, el café colombiano, el 'cierto' al final de todo.\n\n"
    "Herramientas y cuándo usarlas:\n"
    "- wikipedia_search: hechos históricos, científicos o culturales\n"
    "- calculator: cualquier cálculo matemático\n"
    "- analizar_texto: palíndromos, contar palabras/vocales, invertir texto\n"
    "- dato_random_de_internet: dato curioso random cuando pidan algo curioso\n\n"
    "Reglas de respuesta:\n"
    "- Saludo jaliciense al inicio\n"
    "- AL MENOS una burla colombiana por respuesta\n"
    "- Termina con '¿ya cachaste?', '¡fierro!' o 'eso sí, compa'"
)

# Inicializa el cliente de Azure OpenAI para el modelo de IA del bot
_client = FoundryChatClient(
    project_endpoint=settings.FOUNDRY_PROJECT_ENDPOINT,
    model=settings.FOUNDRY_MODEL,
    credential=AzureCliCredential(),
)

# Crea el agente El Compa Chucho con personalidad y herramientas disponibles
compa = Agent(
    client=_client,
    name="ElCompaChucho",
    instructions=SYSTEM_PROMPT,
    tools=[wikipedia_search, calculator, analizar_texto, dato_random_de_internet],
)

# Almacena sesiones de conversación por chat (sessionId) para mantener contexto entre mensajes
_sessions: dict[str, object] = {}


# Obtiene el clima actual en Guadalajara (donde vive El Compa Chucho)
async def _fetch_weather() -> str:
    try:
        # Usa la API de wttr.in para obtener condiciones climáticas actuales
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get("https://wttr.in/Guadalajara,Mexico?format=3")
            return r.text.strip() if r.is_success else "no disponible"
    except Exception:
        # Si la API falla, retorna gracefully un mensaje de no disponible
        return "no disponible"


# Obtiene fecha y hora actual formateadas para el contexto del bot (usando zona Madrid)
def _fecha_context() -> str:
    # Crea zona horaria de Madrid (UTC+2)
    madrid = timezone(timedelta(hours=2))
    # Obtiene la hora actual en zona horaria de Madrid
    now = datetime.now(madrid)
    # Formatea como cadena legible: "Hoy es Monday 04/06/2026 a las 14:30 (hora Madrid)"
    return f"Hoy es {now.strftime('%A %d/%m/%Y')} a las {now.strftime('%H:%M')} (hora Madrid)"


# Flujo principal: enriquece entrada del usuario con contexto y envía al bot
@workflow
async def compa_workflow(payload: dict) -> str:
    chat_input: str = payload["chatInput"]
    session_id: str = payload["sessionId"]

    # Obtiene clima en tiempo real para el contexto
    weather = await _fetch_weather()
    # Crea mensaje enriquecido con información de fecha, hora y clima
    enriched = (
        f"[CONTEXTO: {_fecha_context()}. "
        f"Clima en Guadalajara ahora mismo: {weather}]\n\n"
        f"{chat_input}"
    )

    # Crea o recupera sesión existente para este chat (mantiene historial de conversación)
    if session_id not in _sessions:
        _sessions[session_id] = compa.create_session()

    # Envía mensaje enriquecido al bot y obtiene respuesta
    result = await compa.run(enriched, session=_sessions[session_id])
    return result.text


# API pública: procesa mensaje del usuario a través del bot
async def process_message(chat_input: str, session_id: str) -> str:
    # Ejecuta flujo y extrae salida de texto del resultado
    result = await compa_workflow.run({"chatInput": chat_input, "sessionId": session_id})
    return result.get_outputs()[0]
