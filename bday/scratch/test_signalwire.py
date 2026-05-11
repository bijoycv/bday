import os
import sys
import django
from dotenv import load_dotenv

# Setup Django environment
sys.path.append('/Volumes/Playground/My Office Works/Birthday-Wishes/bday')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bday.settings')
django.setup()

from birthday.utils import fetch_signalwire_messages, _to_e164

def test_signalwire_connection():
    load_dotenv()
    sw_number = _to_e164(os.getenv('TWILIO_PHONE_NUMBER', ''))
    print(f"Testing SignalWire connection for number: {sw_number}")
    
    messages, error = fetch_signalwire_messages(sw_number, limit=5)
    
    if error:
        print(f"❌ Error: {error}")
    else:
        print(f"✅ Success! Fetched {len(messages)} messages.")
        for msg in messages:
            print(f"- [{msg['created_at']}] {msg['direction']}: {msg['body'][:50]}...")

if __name__ == "__main__":
    test_signalwire_connection()
