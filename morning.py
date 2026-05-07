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

    # 하네스 브리핑 업데이트
    briefing = {
        "project": "gookeo",
        "role": "아침",
        "updated_at": now.strftime("%Y-%m-%d"),
        "done_today": f"- 고사성어 3개 발송 완료 ({now.strftime('%Y-%m-%d %H:%M KST')})\n- 발송 항목: {', '.join(i['word'] for i in items)}",
        "todo": "- 내일 아침 7시 자동 발송 예정",
        "analysis": {
            "title": "아침 고사성어 발송 현황",
            "question": "고사성어 데이터가 충분한가?",
            "recommendation": f"현재 {total}개 수집 완료. 3개씩 발송 시 {total//3}일치.",
            "items": [{"rank": 1, "type": "발송 정상", "score": "★★★★★", "reason": "텔레그램 채널 발송 완료", "data_source": "morning.py", "risk": "없음"}],
            "next_action": "고사성어 추가 수집 필요 시 fetch_gosaseongeo.py 재실행"
        },
        "notes": f"총 {total}개 수집 / 진행: {idx+3}번째"
    }
    briefing_path = Path("/home/ubuntu/harness/briefings/gookeo_아침.json")
    if briefing_path.parent.exists():
        import json as _json
        briefing_path.write_text(_json.dumps(briefing, ensure_ascii=False, indent=2))

    print(f"[완료] {idx}~{idx+2}번 발송")


if __name__ == "__main__":
    main()
