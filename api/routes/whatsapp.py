# whatsapp.py — POST /whatsapp (Twilio webhook)
# api/routes/whatsapp.py
# Twilio sends a POST request to this endpoint when someone
# messages your Za6zo WhatsApp number.

from fastapi import APIRouter, Form
from twilio.twiml.messaging_response import MessagingResponse
from bot.rag_chain import ask_zabot

router = APIRouter()

@app.post("/whatsapp")
async def whatsapp_webhook(Body: str = Form(...), From: str = Form(...)):
    """
    Twilio webhook for WhatsApp messages.
    'Body' = the message text
    'From' = the sender's WhatsApp number
    """
    user_message = Body.strip()
    print(f"📱 WhatsApp message from {From}: {user_message}")

    # Get ZaBot's answer
    bot_reply = ask_zabot(user_message)

    # Format response in Twilio's TwiML format
    response = MessagingResponse()
    response.message(bot_reply)

    return str(response)