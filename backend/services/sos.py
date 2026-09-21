"""Emergency SMS delivery. Twilio is used only when credentials are configured."""
import os
import asyncio
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

def format_indian_number(phone: str) -> str:
    """Normalize 10-digit, 91-prefixed, or +91-prefixed Indian mobile numbers."""
    phone = re.sub(r"[\s\-()]", "", phone.strip())
    if re.fullmatch(r"\+91[6-9]\d{9}", phone):
        return phone
    if re.fullmatch(r"91[6-9]\d{9}", phone):
        return f"+{phone}"
    if re.fullmatch(r"[6-9]\d{9}", phone):
        return f"+91{phone}"
    raise ValueError("Enter a valid Indian mobile number, for example 7550397115 or +917550397115.")

def emergency_message(lat: float, lng: float) -> str:
    return f"🚨 EMERGENCY ALERT 🚨\nUser needs help immediately.\n\nLocation:\nhttps://www.google.com/maps?q={lat},{lng}\n\nPlease respond quickly."

def _configured() -> bool:
    return all(os.getenv(key) for key in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER"))

def _send_sync(to: str, body: str) -> str:
    from twilio.rest import Client
    client = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
    message = client.messages.create(body=body, from_=os.environ["TWILIO_FROM_NUMBER"], to=to)
    return message.sid

async def dispatch_sos(contact_phone: str, lat: float, lng: float) -> dict:
    """Send contact + configured police SMS, or safely report mock delivery in development."""
    contact_phone = format_indian_number(contact_phone)
    body = emergency_message(lat, lng)
    police_phone = os.getenv("POLICE_EMERGENCY_PHONE", "")
    recipients, warnings = [contact_phone], []
    # Never block the emergency contact because a police short code wasn't configured.
    if re.fullmatch(r"\+\d{8,15}", police_phone):
        recipients.append(police_phone)
    elif police_phone:
        warnings.append("Police SMS skipped: POLICE_EMERGENCY_PHONE must use E.164 format.")
    if not _configured():
        # Explicit development mode: no network message is sent without secrets.
        return {"mode": "mock", "recipients": recipients, "message": body, "message_ids": [], "warnings": warnings}
    try:
        message_ids = [await asyncio.to_thread(_send_sync, number, body) for number in recipients]
        return {"mode": "twilio", "recipients": recipients, "message": body, "message_ids": message_ids, "warnings": warnings}
    except Exception as error:
        raise RuntimeError("SMS provider rejected the emergency alert. Check Twilio credentials and E.164 recipient numbers.") from error
