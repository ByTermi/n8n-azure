# Servidor web FastAPI — maneja webhooks de n8n y Telegram
import time
from contextlib import asynccontextmanager
from pathlib import Path

import telegram
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from agent import process_message
from config import settings

# Inicializa cliente del bot de Telegram para enviar mensajes
bot = telegram.Bot(token=settings.TELEGRAM_BOT_TOKEN)

# Mensaje de error para enviar cuando el bot encuentra una excepción
_ERROR_MSG = (
    "🚨 *Chale, compa...* el bot se quedó sin palabras. Inténtalo de nuevo, ¿no?\n\n"
    "_Como dirían los colombianos: 'hágale pueeees' 🇨🇴_"
)


# Envía mensaje a Telegram, falla silenciosamente si no es posible (como continueOnFail de n8n)
async def _try_send_telegram(chat_id: str, text: str, error: bool = False) -> None:
    """Intenta enviar mensaje a chat de Telegram. Si chat_id es inválido, usa ID predeterminado.
    Falla silenciosamente en cualquier error (red, token inválido, etc.)."""
    try:
        # Convierte cadena de chat_id a entero
        resolved = int(chat_id)
    except (ValueError, TypeError):
        # Si chat_id es inválido, intenta usar el ID de respaldo predeterminado
        if not settings.TELEGRAM_DEFAULT_CHAT_ID:
            return
        resolved = int(settings.TELEGRAM_DEFAULT_CHAT_ID)
    try:
        # Formatea mensaje: si error=True envía tal cual, de lo contrario envuelve con firma del bot
        msg = text if error else (
            f"🌮 *El Compa Chucho dice:*\n\n{text}\n\n"
            f"_— Tu cuate de Tlaquepaque, Jalisco 🇲🇽_"
        )
        # Envía mensaje vía API de Telegram con formato Markdown
        await bot.send_message(chat_id=resolved, text=msg, parse_mode="Markdown")
    except Exception:
        # Ignora silenciosamente cualquier error (timeouts, IDs inválidos, etc.)
        pass


# Manejador del ciclo de vida startup/shutdown de la app
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Se ejecuta al iniciar (antes de yield) y al cerrar (después de yield)
    yield


# Inicializa la aplicación FastAPI
app = FastAPI(title="El Compa Chucho Bot 🌮", lifespan=lifespan)

# Sirve archivos estáticos (HTML, CSS, JS) del directorio /static
_static = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=_static), name="static")


# Ruta raíz — sirve la interfaz web
@app.get("/")
async def index():
    return FileResponse(_static / "index.html")


# Endpoint de webhook — recibe mensajes de n8n y otras integraciones
@app.post("/webhook/compa-bot")
async def webhook(request: Request):
    body = await request.json()
    # Soporta tanto nombres de campo 'message' como 'chatInput' para flexibilidad
    chat_input = body.get("message") or body.get("chatInput", "")
    # Usa sessionId de la solicitud, o genera uno con timestamp como respaldo
    session_id = str(body.get("sessionId") or f"wh-{int(time.time())}")
    try:
        # Procesa mensaje a través del bot
        output = await process_message(chat_input, session_id)
        # También intenta enviar respuesta vía Telegram (se ejecuta en paralelo, no bloquea respuesta)
        await _try_send_telegram(session_id, output)
        # Retorna respuesta de éxito con respuesta del bot
        return {"ok": True, "respuesta": output, "bot": "El Compa Chucho 🌮"}
    except Exception as e:
        # Envía notificación de error a Telegram y retorna respuesta de error
        await _try_send_telegram(session_id, _ERROR_MSG, error=True)
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})


# Endpoint de webhook — recibe mensajes de Telegram directamente (cuando Telegram envía actualizaciones a este servidor)
@app.post("/telegram")
async def telegram_handler(request: Request):
    data = await request.json()
    try:
        # Extrae ID de chat y texto del mensaje de actualización de Telegram
        chat_id = str(data["message"]["chat"]["id"])
        text = data["message"].get("text", "")
    except (KeyError, TypeError):
        # Formato de mensaje de Telegram inválido — confirma silenciosamente para prevenir reintentos
        return {"ok": True}

    try:
        # Procesa mensaje a través del bot
        output = await process_message(text, chat_id)
        # Envía respuesta del bot de vuelta al chat de Telegram
        await _try_send_telegram(chat_id, output)
    except Exception:
        # Envía mensaje de error en caso de fallo
        await _try_send_telegram(chat_id, _ERROR_MSG, error=True)

    # Siempre retorna OK para reconocer que se recibió el mensaje (previene reintentos de Telegram)
    return {"ok": True}
