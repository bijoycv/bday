from django.conf import settings
from twilio.rest import Client
import logging
import os

logger = logging.getLogger(__name__)

def send_sms(to_number, body):
    """
    Send an SMS using Twilio.
    Returns:
        bool: True if successful, False otherwise.
        str: Message SID or Error message.
    """
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    from_number = os.getenv('TWILIO_PHONE_NUMBER')

    if not account_sid or not auth_token or not from_number:
        logger.error("Twilio credentials are missing in .env")
        return False, "Twilio credentials missing"

    client = Client(account_sid, auth_token)

    # Normalize phone number (assume US +1 if 10 digits)
    to_number_str = str(to_number).strip()
    if len(to_number_str) == 10 and to_number_str.isdigit():
        to_number_str = f"+1{to_number_str}"
    elif not to_number_str.startswith('+') and to_number_str.isdigit():
         # If it's 11 digits starting with 1, just add +
         if len(to_number_str) == 11 and to_number_str.startswith('1'):
             to_number_str = f"+{to_number_str}"

    try:
        message = client.messages.create(
            body=body,
            from_=from_number,
            to=to_number_str
        )
        logger.info(f"SMS sent successfully. SID: {message.sid}")
        return True, message.sid
    except Exception as e:
        logger.error(f"Failed to send SMS: {e}")
        return False, str(e)
