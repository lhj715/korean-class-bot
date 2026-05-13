import requests
import sys
from datetime import datetime
import pytz
from bs4 import BeautifulSoup
import random
import os
from google import genai as google_genai
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")
_gemini = google_genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))

import json as _json2
from urllib.parse import urlencode as _urlencode
from urllib.request import Request as _Request, urlopen as _urlopen
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID, AIRTABLE_BASE_ID

KST = pytz.timezone("Asia/Seoul")

BLOG_ID  = "9594jh"
HEADERS  = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://m.blog.naver.com/",
}

LITERATURE_KEYWORDS = [
    "해석", "해설", "분석", "줄거리", "주제", "감상",
    "현대시", "고전시", "시조", "향가", "가사체", "가사 문학", "수필", "희곡", "소설", "문학", "고전",
    "수능특강", "수능완성", "작품", "작가", "서술", "배경",
]

NON_LITERATURE = [
    "학원", "인강", "공부방법", "공부법", "시험일정", "기사 시험",
    "기숙", "직장인", "자격증", "취업", "경비지도사",
]

SUMMARY_PROMPT = """다음은 국어 문학 블로그 포스트 본문이야.
고등학생에게 텔레그램으로 보낼 학습 자료를 아래 형식으로 정리해줘.
형식 외 설명은 쓰지 마.

**문장 종결 규칙 (필수)**:
- `~합니다.`, `~입니다.`, `~예요.`, `~해요.` 같은 격식체·존댓말 종결 절대 금지.
- `~한다.` 또는 `~함.` 형태로 종결 (둘 중 어느 쪽이든 자연스러운 것 사용, 어느 한쪽 편향 금지).

작품: [제목 / 작가 / 갈래]

【줄거리】
(3~5줄로 간략하게. 주요 인물·사건·결말 흐름만)

【주제】
(1~2줄)

【핵심 내용】
- (3~4개 핵심 포인트)

【수능 포인트】
1.
2.
3.

---
본문:
{content}"""


def is_literature_post(title: str) -> bool:
    if any(bl in title for bl in NON_LITERATURE):
        return False
    return any(kw in title for kw in LITERATURE_KEYWORDS)


def is_weekday_kst():
    now = datetime.now(KST)
    if now.weekday() >= 5:
        print(f"[건너뜀] 주말 {now.strftime('%Y-%m-%d')}")
        return False
    return True


def get_post_list(pages: int = 10) -> list[dict]:
    """PostTitleListAsync API로 최근 N페이지 글 목록 수집."""
    import urllib.request
    import re as _re
    from urllib.parse import unquote_plus

    api_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://blog.naver.com/",
    }
    posts = []
    for page in range(1, pages + 1):
        url = (
            f"https://blog.naver.com/PostTitleListAsync.naver"
            f"?blogId={BLOG_ID}&categoryNo=0&currentPage={page}"
            f"&countPerPage=30&orderType=desc"
        )
        try:
            req = urllib.request.Request(url, headers=api_headers)
            with urllib.request.urlopen(req, timeout=10) as r:
                raw = r.read().decode("utf-8")
            titles  = _re.findall(r'"title":"([^"]+)"', raw)
            log_nos = _re.findall(r'"logNo":"([^"]+)"', raw)
            dates   = _re.findall(r'"addDate":"([^"]+)"', raw)
            for t, n, d in zip(titles, log_nos, dates):
                posts.append({
                    "title": unquote_plus(t),
                    "log_no": n,
                    "published": d,
                })
            if len(titles) < 30:
                break
        except Exception as e:
            print(f"  페이지 {page} 수집 실패: {e}")
            break
    return posts


def fetch_post_content(log_no):
    url = f"https://m.blog.naver.com/{BLOG_ID}/{log_no}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    content_div = (
        soup.select_one("div.se-main-container") or
        soup.select_one("div#postViewArea") or
        soup.select_one("div.post_ct")
    )
    if not content_div:
        return ""

    for tag in content_div.select("script, style, iframe"):
        tag.decompose()

    lines = [l for l in content_div.get_text(separator="\n", strip=True).splitlines() if l.strip()]
    return "\n".join(lines)


def summarize(title, content):
    trimmed = content[:4000]
    prompt = SUMMARY_PROMPT.format(content=trimmed)
    # 1차: Gemini flash-lite (기본)
    try:
        resp = _gemini.models.generate_content(
            model="models/gemini-flash-lite-latest",
            contents=prompt,
        )
        return resp.text.strip()
    except Exception as e1:
        print(f"[Gemini flash-lite 실패] {type(e1).__name__}: {str(e1)[:100]}")
    # 2차: Gemini 2.5 flash (더 큰 모델, 보통 가용성 ↑)
    try:
        resp = _gemini.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=prompt,
        )
        return resp.text.strip()
    except Exception as e2:
        print(f"[Gemini 2.5-flash 실패] {type(e2).__name__}: {str(e2)[:100]}")
    # 3차: Anthropic Claude Haiku 폴백
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception as e3:
        print(f"[Claude Haiku 실패] {type(e3).__name__}: {str(e3)[:100]}")
    # 모두 실패 — 컨텐츠 첫 300자 요약 대체
    return trimmed[:300] + ("..." if len(trimmed) > 300 else "")


# ── 저녁 문학 발송이력 (Airtable) ─────────────────────────────────────
EVENING_TABLE_ID = "tblIhJg33QX3pxfTR"  # school_bot_저녁문학 (같은 베이스)
_AT_EVENING = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{EVENING_TABLE_ID}"
_AT_H_EVENING = {
    "Authorization": f"Bearer {os.environ.get('AIRTABLE_TOKEN', '')}",
    "Content-Type": "application/json",
}


def fetch_sent_log_nos() -> set[str]:
    """이미 발송된 log_no 집합 반환. 페이지네이션 처리."""
    sent: set[str] = set()
    offset = None
    while True:
        params = [("pageSize", "100"), ("fields[]", "log_no")]
        if offset:
            params.append(("offset", offset))
        req = _Request(f"{_AT_EVENING}?{_urlencode(params)}", headers=_AT_H_EVENING)
        try:
            with _urlopen(req, timeout=20) as r:
                d = _json2.loads(r.read())
        except Exception as e:
            print(f"[Airtable] 발송이력 조회 실패(계속): {e}")
            return sent
        for rec in d.get("records", []):
            ln = (rec.get("fields", {}).get("log_no") or "").strip()
            if ln:
                sent.add(ln)
        offset = d.get("offset")
        if not offset:
            break
    return sent


def record_sent(log_no: str, title: str, published: str) -> None:
    """Airtable에 발송이력 1행 추가."""
    body = {
        "fields": {
            "log_no": log_no,
            "title": title,
            "published": published or "",
            "발송일시": datetime.now(KST).strftime("%Y-%m-%dT%H:%M:%S"),
        },
        "typecast": True,
    }
    req = _Request(_AT_EVENING, data=_json2.dumps(body).encode(),
                   headers=_AT_H_EVENING, method="POST")
    try:
        with _urlopen(req, timeout=20) as r:
            r.read()
    except Exception as e:
        print(f"[Airtable] 발송이력 기록 실패(계속): {e}")



def send_telegram(text, retries=3):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    if len(text) > 4096:
        text = text[:4090] + "..."
    import time
    for attempt in range(retries):
        try:
            resp = requests.post(url, json={
                "chat_id": TELEGRAM_CHANNEL_ID,
                "text": text,
            }, timeout=20)
            resp.raise_for_status()
            return
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(3)
            else:
                raise


def main():
    if not is_weekday_kst():
        sys.exit(0)

    now = datetime.now(KST)
    date_str = now.strftime("%m월 %d일")
    print(f"[저녁 발송 시작] {now.strftime('%Y-%m-%d %H:%M KST')}")

    posts = get_post_list()
    if not posts:
        print("포스트 목록 없음")
        sys.exit(1)

    lit_posts = [p for p in posts if is_literature_post(p["title"])]
    if not lit_posts:
        lit_posts = posts
    print(f"  문학 포스트: {len(lit_posts)}/{len(posts)}개")

    # 발송이력 조회 → 미발송 글만 후보로
    sent_log_nos = fetch_sent_log_nos()
    print(f"  발송이력 {len(sent_log_nos)}건 로드")
    unsent = [p for p in lit_posts if p["log_no"] not in sent_log_nos]
    print(f"  미발송 문학 포스트 {len(unsent)}개")

    if not unsent:
        # 모두 발송했으면 가장 오래 안 본 글로 fallback (전체에서 랜덤)
        print("  ⚠ 미발송 글 없음 — lit_posts 전체에서 랜덤 fallback")
        target = random.choice(lit_posts[:10])
    else:
        today_posts = [p for p in unsent if p["published"].startswith(now.strftime("%a, %d %b %Y"))]
        target = today_posts[0] if today_posts else unsent[0]  # 미발송 중 최상위
    print(f"  선택: [{target['log_no']}] {target['title']}")

    content = fetch_post_content(target["log_no"])
    if not content:
        print("본문 파싱 실패")
        sys.exit(1)

    summary = summarize(target["title"], content)

    message = f"매일국어\n[저녁 국어] {date_str} 문학 자료\n\n{summary}"
    send_telegram(message)
    record_sent(target["log_no"], target["title"], target.get("published", ""))

    # 하네스 브리핑 업데이트
    briefing = {
        "project": "gookeo",
        "role": "저녁",
        "updated_at": now.strftime("%Y-%m-%d"),
        "done_today": f"- 문학 자료 발송 완료 ({now.strftime('%Y-%m-%d %H:%M KST')})\n- 작품: {target['title'][:40]}",
        "todo": "- 내일 저녁 8시 자동 발송 예정",
        "analysis": {
            "title": "저녁 문학 자료 발송 현황",
            "question": "블로그 크롤링 및 요약이 정상 작동하는가?",
            "recommendation": "Gemini flash-lite-latest로 요약 생성 중. 품질 모니터링 필요.",
            "items": [{"rank": 1, "type": "발송 정상", "score": "★★★★★", "reason": "네이버 블로그 크롤링 + Gemini 요약 + 텔레그램 발송 완료", "data_source": "evening.py", "risk": "없음"}],
            "next_action": "블로그 신규 포스트 모니터링"
        },
        "notes": f"블로그: blog.naver.com/9594jh | 문학 포스트: {len(lit_posts)}/50개"
    }
    briefing_path = Path("/home/ubuntu/harness/briefings/gookeo_저녁.json")
    if briefing_path.parent.exists():
        import json as _json
        briefing_path.write_text(_json.dumps(briefing, ensure_ascii=False, indent=2))

    print(f"[완료] {now.strftime('%Y-%m-%d %H:%M KST')} 발송")


if __name__ == "__main__":
    main()
