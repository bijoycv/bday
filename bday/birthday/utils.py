import logging
import os
import requests

logger = logging.getLogger(__name__)


def _get_signalwire_credentials():
    """Return (project_id, api_token, space_url, from_number) or raise."""
    project_id = os.getenv('SIGNALWIRE_PROJECT_ID')
    api_token = os.getenv('SIGNALWIRE_API_TOKEN')
    space_url = os.getenv('SIGNALWIRE_SPACE_URL')
    from_number = os.getenv('TWILIO_PHONE_NUMBER')  # Same number, ported to SignalWire
    return project_id, api_token, space_url, from_number


def _to_e164(number):
    """Normalize phone numbers to E.164 format (+1XXXXXXXXXX)."""
    if not number:
        return ''
    raw = str(number).strip()
    digits = ''.join(ch for ch in raw if ch.isdigit())
    if len(digits) == 10:
        return f'+1{digits}'
    if len(digits) == 11 and digits.startswith('1'):
        return f'+{digits}'
    return raw if raw.startswith('+') else f'+{digits}' if digits else raw


def send_sms(to_number, body):
    """
    Send an SMS using SignalWire Compatibility REST API.
    Returns:
        bool: True if successful, False otherwise.
        str: Message SID or Error message.
    """
    project_id, api_token, space_url, from_number = _get_signalwire_credentials()

    if not project_id or not api_token or not space_url or not from_number:
        logger.error("SignalWire credentials are missing in .env")
        return False, "SignalWire credentials missing"

    # Normalize phone numbers to E.164
    to_str = _to_e164(to_number)
    from_str = _to_e164(from_number)

    url = f"https://{space_url}/api/laml/2010-04-01/Accounts/{project_id}/Messages.json"

    try:
        resp = requests.post(
            url,
            auth=(project_id, api_token),
            data={
                'From': from_str,
                'To': to_str,
                'Body': body,
            },
            timeout=15,
        )
        data = resp.json()

        if resp.status_code in (200, 201):
            sid = data.get('sid', '')
            logger.info(f"SMS sent successfully via SignalWire. SID: {sid}")
            return True, sid
        else:
            error_msg = data.get('message', '') or data.get('error', '') or resp.text
            logger.error(f"SignalWire send failed ({resp.status_code}): {error_msg}")
            return False, error_msg

    except Exception as e:
        logger.error(f"Failed to send SMS via SignalWire: {e}")
        return False, str(e)


def fetch_signalwire_messages(sw_number, limit=120):
    """
    Fetch recent SMS messages from SignalWire Compatibility API.
    Returns (list_of_message_dicts, error_string_or_None).
    """
    project_id, api_token, space_url, _ = _get_signalwire_credentials()
    if not project_id or not api_token or not space_url or not sw_number:
        return [], 'SignalWire credentials or number are missing in .env'

    base_url = f"https://{space_url}/api/laml/2010-04-01/Accounts/{project_id}/Messages.json"

    try:
        # Fetch inbound (to our number)
        resp_in = requests.get(
            base_url,
            auth=(project_id, api_token),
            params={'To': sw_number, 'PageSize': limit},
            timeout=15,
        )
        inbound = resp_in.json().get('messages', []) if resp_in.status_code == 200 else []

        # Fetch outbound (from our number)
        resp_out = requests.get(
            base_url,
            auth=(project_id, api_token),
            params={'From': sw_number, 'PageSize': limit},
            timeout=15,
        )
        outbound = resp_out.json().get('messages', []) if resp_out.status_code == 200 else []

        # Check for auth errors
        if resp_in.status_code == 401 or resp_out.status_code == 401:
            return [], 'SignalWire authentication failed — check your API Token (must be a REST API token, not a PSK token)'

        merged = {}
        from django.utils import timezone as tz
        from datetime import datetime

        for msg in inbound + outbound:
            sid = msg.get('sid', f"tmp-{id(msg)}")
            msg_from = _to_e164(msg.get('from', ''))
            msg_to = _to_e164(msg.get('to', ''))
            direction = 'Outbound' if msg_from == sw_number else 'Inbound'

            # Parse date
            date_str = msg.get('date_sent') or msg.get('date_created') or ''
            try:
                created_at = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z') if date_str else tz.now()
            except (ValueError, TypeError):
                created_at = tz.now()

            merged[sid] = {
                'sid': sid,
                'from_number': msg_from,
                'to_number': msg_to,
                'direction': direction,
                'status': (msg.get('status', '') or '').title(),
                'body': msg.get('body', '') or '',
                'created_at': created_at,
                'gateway_number': sw_number,
            }

        feed = sorted(merged.values(), key=lambda x: x['created_at'], reverse=True)
        return feed, None

    except Exception as exc:
        return [], f'Unable to fetch live SignalWire feed: {exc}'
