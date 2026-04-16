import os
import requests
from dotenv import load_dotenv

load_dotenv()

def send_smart_reminder(event_type: str, description: str, days_left: int):
    print("\n" + "="*90)
    print(f"[SMART REMINDER]: Your {event_type} is happening in {days_left} days!")
    print(f"   -> {description}")
    print("="*90 + "\n")

