import json
import requests
import sys
from datetime import datetime
from pathlib import Path
import pytz

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID

KST = pytz.timezone("Asia/Seoul")
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"


def is_weekday_kst():
    now = datetime.now(KST)
    weekday = now.weekday()  # 0=월, 4=금, 5=토, 6=일
    if weekday >= 5:
        print(f"[건너뜀] {now.strftime('%Y-%m-%d %A')} - 주말")
        return False
    return True


def load_data():
    with open(DATA_DIR / "gosaseongeo.json", encoding="utf-8") as f:
        return json.load(f)


def load_progress():
    path = DATA_DIR / "progress.json"
    if not path.exists():
        return {"morning_index": 0}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_progress(progress):
    with open(DATA_DIR / "progress.json", "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def build_message(items, date_str):
    lines = ["매일국어", f"[오전 국어] {date_str} 오늘의 고사성어"]
    for i, item in enumerate(items, 1):
        lines.append("")
        lines.append(f"{i}. {item['word']}({item['hanja']}): {item['meaning']}")
    return "\n".join(lines)


def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(url, json={
        "chat_id": TELEGRAM_CHANNEL_ID,
        "text": text,
    }, timeout=10)
    resp.raise_for_status()


def main():
    if not is_weekday_kst():
        sys.exit(0)

    now = datetime.now(KST)
    date_str = now.strftime("%m월 %d일")
    print(f"[아침 발송 시작] {now.strftime('%Y-%m-%d %H:%M KST')}")

    data = load_data()
    progress = load_progress()
    idx = progress.get("morning_index", 0)
    total = len(data)

    items = [data[(idx + i) % total] for i in range(3)]
    message = build_message(items, date_str)

    send_telegram(message)

    progress["morning_index"] = (idx + 3) % total
    save_progress(progress)
    print(f"[완료] {idx}~{idx+2}번 발송")


if __name__ == "__main__":
    main()
