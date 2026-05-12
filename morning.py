"""아침 고사성어 발송 (평일 07:45 KST cron).

데이터 출처: Airtable `school_bot_고사성어` 테이블
선택 규칙: 발송횟수 오름차순 → 동률이면 index 오름차순 → 상위 3개
발송 후: 발송횟수+1, 최근발송일=오늘, 발송이력에 오늘 날짜 prepend
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pytz
import requests

from config import (
    AIRTABLE_BASE_ID,
    AIRTABLE_TABLE_ID,
    AIRTABLE_TOKEN,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHANNEL_ID,
)

KST = pytz.timezone("Asia/Seoul")
AT_API = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_ID}"
AT_HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_TOKEN}",
    "Content-Type": "application/json",
}


def is_weekday_kst():
    now = datetime.now(KST)
    if now.weekday() >= 5:
        print(f"[건너뜀] {now.strftime('%Y-%m-%d %A')} - 주말")
        return False
    return True


def pick_three_from_airtable():
    """발송횟수 asc → index asc 정렬해서 상위 3개 가져옴."""
    qs = urlencode([
        ("pageSize", "3"),
        ("sort[0][field]", "발송횟수"),
        ("sort[0][direction]", "asc"),
        ("sort[1][field]", "index"),
        ("sort[1][direction]", "asc"),
        ("fields[]", "index"),
        ("fields[]", "word"),
        ("fields[]", "hanja"),
        ("fields[]", "meaning"),
        ("fields[]", "example"),
        ("fields[]", "발송횟수"),
        ("fields[]", "발송이력"),
    ])
    req = Request(f"{AT_API}?{qs}", headers=AT_HEADERS)
    with urlopen(req, timeout=20) as r:
        d = json.loads(r.read())
    return d.get("records", [])


def update_airtable(records, today_iso):
    """발송된 3개 레코드에 발송횟수+1, 최근발송일, 발송이력 prepend."""
    updates = []
    for rec in records:
        f = rec.get("fields", {})
        cur_count = int(f.get("발송횟수", 0) or 0)
        prev_history = f.get("발송이력", "") or ""
        new_history = today_iso if not prev_history else f"{today_iso},{prev_history}"
        updates.append({
            "id": rec["id"],
            "fields": {
                "발송횟수": cur_count + 1,
                "최근발송일": today_iso,
                "발송이력": new_history,
            },
        })
    body = {"records": updates}
    req = Request(AT_API, data=json.dumps(body).encode(), headers=AT_HEADERS, method="PATCH")
    with urlopen(req, timeout=20) as r:
        r.read()


def build_message(items, date_str):
    lines = ["매일국어", f"[오전 국어] {date_str} 오늘의 고사성어"]
    for i, item in enumerate(items, 1):
        lines.append("")
        f = item.get("fields", {})
        lines.append(f"{i}. {f.get('word','')}({f.get('hanja','')}): {f.get('meaning','')}")
    return "\n".join(lines)


def send_telegram(text, retries=3):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    for attempt in range(retries):
        try:
            resp = requests.post(url, json={
                "chat_id": TELEGRAM_CHANNEL_ID,
                "text": text,
            }, timeout=20)
            resp.raise_for_status()
            return
        except Exception:
            if attempt < retries - 1:
                time.sleep(3)
            else:
                raise


def main():
    if not is_weekday_kst():
        sys.exit(0)

    now = datetime.now(KST)
    date_str = now.strftime("%m월 %d일")
    today_iso = now.strftime("%Y-%m-%d")
    print(f"[아침 발송 시작] {now.strftime('%Y-%m-%d %H:%M KST')}")

    items = pick_three_from_airtable()
    if len(items) < 3:
        print(f"[중단] Airtable에서 3개 못 가져옴 (현재 {len(items)}개)")
        sys.exit(1)

    words = [it.get("fields", {}).get("word", "") for it in items]
    indices = [it.get("fields", {}).get("index", "?") for it in items]
    print(f"  선택: {list(zip(indices, words))}")

    message = build_message(items, date_str)
    send_telegram(message)
    update_airtable(items, today_iso)

    # 하네스 브리핑 업데이트
    briefing = {
        "project": "gookeo",
        "role": "아침",
        "updated_at": today_iso,
        "done_today": (
            f"- 고사성어 3개 발송 완료 ({now.strftime('%Y-%m-%d %H:%M KST')})\n"
            f"- 발송 항목: {', '.join(words)}"
        ),
        "todo": "- 내일 아침 7시 45분 자동 발송 예정",
        "analysis": {
            "title": "아침 고사성어 발송 현황",
            "question": "Airtable 동기화 정상?",
            "recommendation": "Airtable 발송횟수·발송이력 자동 누적",
            "items": [{
                "rank": 1, "type": "발송 정상", "score": "★★★★★",
                "reason": "텔레그램+Airtable 동기화 성공",
                "data_source": "Airtable + Telegram", "risk": "없음",
            }],
            "next_action": "Airtable 시트에서 발송이력 누적 확인",
        },
        "notes": f"Airtable BASE={AIRTABLE_BASE_ID} TABLE={AIRTABLE_TABLE_ID}",
    }
    briefing_path = Path("/home/ubuntu/harness/briefings/gookeo_아침.json")
    if briefing_path.parent.exists():
        briefing_path.write_text(
            json.dumps(briefing, ensure_ascii=False, indent=2)
        )

    print(f"[완료] 발송: {', '.join(words)}")


if __name__ == "__main__":
    main()
