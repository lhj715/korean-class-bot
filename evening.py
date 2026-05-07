import requests
import sys
from datetime import datetime
import pytz
from bs4 import BeautifulSoup
import feedparser
import random
import os
from google import genai as google_genai
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")
_gemini = google_genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID

KST = pytz.timezone("Asia/Seoul")

BLOG_ID  = "9594jh"
RSS_URL  = f"https://rss.blog.naver.com/{BLOG_ID}.xml"
HEADERS  = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://m.blog.naver.com/",
}

LITERATURE_KEYWORDS = [
    "해석", "해설", "분석", "줄거리", "주제", "감상",
    "소설", "시", "수필", "희곡", "문학", "고전",
    "수능", "내신", "작품", "작가", "서술", "배경",
]

SUMMARY_PROMPT = """다음은 국어 문학 블로그 포스트 본문이야.
고등학생에게 텔레그램으로 보낼 학습 자료를 아래 형식으로 정리해줘.
형식 외 설명은 쓰지 마.

작품: [제목 / 작가 / 갈래]

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


def is_literature_post(title):
    return any(kw in title for kw in LITERATURE_KEYWORDS)


def is_weekday_kst():
    now = datetime.now(KST)
    if now.weekday() >= 5:
        print(f"[건너뜀] 주말 {now.strftime('%Y-%m-%d')}")
        return False
    return True


def get_post_list():
    feed = feedparser.parse(RSS_URL)
    posts = []
    for entry in feed.entries:
        link = entry.get("link", "")
        log_no = link.rstrip("/").split("/")[-1].split("?")[0]
        if log_no.isdigit():
            posts.append({
                "title": entry.get("title", ""),
                "log_no": log_no,
                "published": entry.get("published", ""),
            })
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
    resp = _gemini.models.generate_content(
        model="models/gemini-flash-lite-latest",
        contents=SUMMARY_PROMPT.format(content=trimmed)
    )
    return resp.text.strip()


def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    if len(text) > 4096:
        text = text[:4090] + "..."
    resp = requests.post(url, json={
        "chat_id": TELEGRAM_CHANNEL_ID,
        "text": text,
    }, timeout=15)
    resp.raise_for_status()


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

    today_posts = [p for p in lit_posts if p["published"].startswith(now.strftime("%a, %d %b %Y"))]
    target = today_posts[0] if today_posts else random.choice(lit_posts[:10])
    print(f"  선택: [{target['log_no']}] {target['title']}")

    content = fetch_post_content(target["log_no"])
    if not content:
        print("본문 파싱 실패")
        sys.exit(1)

    summary = summarize(target["title"], content)

    message = f"매일국어\n[저녁 국어] {date_str} 문학 자료\n\n{summary}"
    send_telegram(message)
    print(f"[완료] 발송")


if __name__ == "__main__":
    main()
