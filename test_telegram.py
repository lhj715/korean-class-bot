import requests
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")

token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
channel = os.environ.get("TELEGRAM_CHANNEL_ID", "")

print(f"토큰: {token[:20]}...")
print(f"채널: {channel}")

r = requests.post(
    f"https://api.telegram.org/bot{token}/sendMessage",
    json={"chat_id": channel, "text": "국어수업봇 테스트 메시지입니다."},
    timeout=10
)
print(f"결과: {r.status_code} ok={r.json().get('ok')} {r.json().get('description','')}")
