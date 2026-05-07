"""
서버 초기 설정: .env 확인 + cron 등록 + 텔레그램 확인 메시지 발송
실행: python3 init_server.py
"""
import os
import subprocess
import requests
from pathlib import Path
from dotenv import load_dotenv

BASE = Path(__file__).parent
load_dotenv(BASE / ".env")

TOKEN   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHANNEL = os.environ.get("TELEGRAM_CHANNEL_ID", "")
VENV    = BASE / "venv/bin/python3"

results = []

# 1. .env 확인
results.append(f"토큰: {'OK' if TOKEN else 'MISSING'}")
results.append(f"채널: {'OK' if CHANNEL else 'MISSING'}")

# 2. cron 등록
MORNING = f"0 22 * * 0-4 cd {BASE} && source {BASE}/venv/bin/activate && python3 morning.py >> /tmp/school_morning.log 2>&1"
EVENING = f"0 11 * * 1-5 cd {BASE} && source {BASE}/venv/bin/activate && python3 evening.py >> /tmp/school_evening.log 2>&1"

try:
    current = subprocess.check_output("crontab -l 2>/dev/null || true", shell=True).decode()
    lines = [l for l in current.splitlines() if "school_bot" not in l and l.strip()]
    lines += [
        "# school_bot 아침 7:00 KST",
        MORNING,
        "# school_bot 저녁 20:00 KST",
        EVENING,
    ]
    new_cron = "\n".join(lines) + "\n"
    proc = subprocess.run("crontab -", input=new_cron, shell=True, text=True, capture_output=True)
    if proc.returncode == 0:
        results.append("cron 등록: OK")
    else:
        results.append(f"cron 오류: {proc.stderr}")
except Exception as e:
    results.append(f"cron 예외: {e}")

# 3. cron 확인
try:
    crontab = subprocess.check_output("crontab -l", shell=True).decode()
    cron_lines = [l for l in crontab.splitlines() if "school" in l and not l.startswith("#")]
    results.append(f"등록된 cron {len(cron_lines)}개: OK")
except:
    results.append("cron 확인 실패")

# 4. 텔레그램으로 결과 보고
msg = "[ school_bot 서버 설정 완료 ]\n\n" + "\n".join(f"• {r}" for r in results)
resp = requests.post(
    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
    json={"chat_id": CHANNEL, "text": msg},
    timeout=10
)
print(msg)
print(f"\n텔레그램 전송: {resp.json().get('ok')}")
