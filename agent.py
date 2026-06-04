# Agent configuration and workflow for El Compa Chucho bot
from datetime import datetime, timezone, timedelta

import httpx
from agent_framework import Agent, workflow
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential

from config import settings
from tools import analizar_texto, calculator, dato_random_de_internet, wikipedia_search

# Define bot personality and behavior rules
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

# Initialize Azure OpenAI client for the bot's AI model
_client = FoundryChatClient(
    project_endpoint=settings.FOUNDRY_PROJECT_ENDPOINT,
    model=settings.FOUNDRY_MODEL,
    credential=AzureCliCredential(),
)

# Create the El Compa Chucho agent with personality and available tools
compa = Agent(
    client=_client,
    name="ElCompaChucho",
    instructions=SYSTEM_PROMPT,
    tools=[wikipedia_search, calculator, analizar_texto, dato_random_de_internet],
)

# Store conversation sessions per chat (sessionId) to maintain context across multiple messages
_sessions: dict[str, object] = {}


# Fetch current weather in Guadalajara (where El Compa Chucho lives)
async def _fetch_weather() -> str:
    try:
        # Use wttr.in API to get current weather conditions
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get("https://wttr.in/Guadalajara,Mexico?format=3")
            return r.text.strip() if r.is_success else "no disponible"
    except Exception:
        # If API fails, gracefully return unavailable message
        return "no disponible"


# Get current date and time formatted for the bot's context (using Madrid timezone)
def _fecha_context() -> str:
    # Create Madrid timezone (UTC+2)
    madrid = timezone(timedelta(hours=2))
    # Get current time in Madrid timezone
    now = datetime.now(madrid)
    # Format as readable string: "Today is Monday 04/06/2026 at 14:30 (Madrid time)"
    return f"Hoy es {now.strftime('%A %d/%m/%Y')} a las {now.strftime('%H:%M')} (hora Madrid)"


# Main workflow: enriches user input with context and sends to the bot
@workflow
async def compa_workflow(payload: dict) -> str:
    chat_input: str = payload["chatInput"]
    session_id: str = payload["sessionId"]

    # Fetch real-time weather for context
    weather = await _fetch_weather()
    # Create enriched prompt with date, time, and weather information
    enriched = (
        f"[CONTEXTO: {_fecha_context()}. "
        f"Clima en Guadalajara ahora mismo: {weather}]\n\n"
        f"{chat_input}"
    )

    # Create or retrieve existing session for this chat (maintains conversation history)
    if session_id not in _sessions:
        _sessions[session_id] = compa.create_session()

    # Send enriched message to bot and get response
    result = await compa.run(enriched, session=_sessions[session_id])
    return result.text


# Public API: process user message through the bot
async def process_message(chat_input: str, session_id: str) -> str:
    # Run workflow and extract text output from result
    result = await compa_workflow.run({"chatInput": chat_input, "sessionId": session_id})
    return result.get_outputs()[0]
