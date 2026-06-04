# FastAPI web server — handles webhooks from n8n and Telegram
import time
from contextlib import asynccontextmanager
from pathlib import Path

import telegram
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from agent import process_message
from config import settings

# Initialize Telegram bot client for sending messages
bot = telegram.Bot(token=settings.TELEGRAM_BOT_TOKEN)

# Error message to send when bot encounters an exception
_ERROR_MSG = (
    "🚨 *Chale, compa...* el bot se quedó sin palabras. Inténtalo de nuevo, ¿no?\n\n"
    "_Como dirían los colombianos: 'hágale pueeees' 🇨🇴_"
)


# Send message to Telegram, silently failing if not possible (like n8n's continueOnFail)
async def _try_send_telegram(chat_id: str, text: str, error: bool = False) -> None:
    """Attempts to send message to Telegram chat. If chat_id is invalid, uses fallback default ID.
    Fails silently on any error (network, invalid token, etc.)."""
    try:
        # Convert chat_id string to integer
        resolved = int(chat_id)
    except (ValueError, TypeError):
        # If chat_id is invalid, try using default fallback chat ID
        if not settings.TELEGRAM_DEFAULT_CHAT_ID:
            return
        resolved = int(settings.TELEGRAM_DEFAULT_CHAT_ID)
    try:
        # Format message: if error=True send as-is, otherwise wrap with bot signature
        msg = text if error else (
            f"🌮 *El Compa Chucho dice:*\n\n{text}\n\n"
            f"_— Tu cuate de Tlaquepaque, Jalisco 🇲🇽_"
        )
        # Send message via Telegram API with Markdown formatting
        await bot.send_message(chat_id=resolved, text=msg, parse_mode="Markdown")
    except Exception:
        # Silently ignore any errors (network timeouts, invalid IDs, etc.)
        pass


# App startup/shutdown lifecycle handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs on startup (before yield) and shutdown (after yield)
    yield


# Initialize FastAPI app
app = FastAPI(title="El Compa Chucho Bot 🌮", lifespan=lifespan)

# Serve static files (HTML, CSS, JS) from /static directory
_static = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=_static), name="static")


# Root route — serves the web interface
@app.get("/")
async def index():
    return FileResponse(_static / "index.html")


# Webhook endpoint — receives messages from n8n and other integrations
@app.post("/webhook/compa-bot")
async def webhook(request: Request):
    body = await request.json()
    # Support both 'message' and 'chatInput' field names for flexibility
    chat_input = body.get("message") or body.get("chatInput", "")
    # Use sessionId from request, or generate a timestamped fallback
    session_id = str(body.get("sessionId") or f"wh-{int(time.time())}")
    try:
        # Process message through bot
        output = await process_message(chat_input, session_id)
        # Also attempt to send response via Telegram (runs in parallel, doesn't block response)
        await _try_send_telegram(session_id, output)
        # Return success response with bot's answer
        return {"ok": True, "respuesta": output, "bot": "El Compa Chucho 🌮"}
    except Exception as e:
        # Send error notification to Telegram and return error response
        await _try_send_telegram(session_id, _ERROR_MSG, error=True)
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})


# Webhook endpoint — receives Telegram messages directly (when Telegram sends updates to this server)
@app.post("/telegram")
async def telegram_handler(request: Request):
    data = await request.json()
    try:
        # Extract chat ID and message text from Telegram update
        chat_id = str(data["message"]["chat"]["id"])
        text = data["message"].get("text", "")
    except (KeyError, TypeError):
        # Invalid Telegram message format — silently acknowledge to prevent retries
        return {"ok": True}

    try:
        # Process message through bot
        output = await process_message(text, chat_id)
        # Send bot's response back to Telegram chat
        await _try_send_telegram(chat_id, output)
    except Exception:
        # Send error message on failure
        await _try_send_telegram(chat_id, _ERROR_MSG, error=True)

    # Always return OK to acknowledge message received (prevents Telegram from retrying)
    return {"ok": True}
