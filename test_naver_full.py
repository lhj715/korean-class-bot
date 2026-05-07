import requests
import feedparser
from bs4 import BeautifulSoup

BLOG_ID = "9594jh"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://m.blog.naver.com/",
}

feed = feedparser.parse(f"https://rss.blog.naver.com/{BLOG_ID}.xml")
posts = []
for e in feed.entries:
    link = e.get("link", "")
    log_no = link.rstrip("/").split("/")[-1].split("?")[0]
    if log_no.isdigit():
        posts.append({"title": e.title[:40], "log_no": log_no})

print(f"RSS 포스트 수: {len(posts)}개\n")

ok, fail, no_content = 0, 0, 0
for p in posts[:10]:
    url = f"https://m.blog.naver.com/{BLOG_ID}/{p['log_no']}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        div = (
            soup.select_one("div.se-main-container") or
            soup.select_one("div#postViewArea") or
            soup.select_one("div.post_ct")
        )
        text_len = len(div.get_text(strip=True)) if div else 0
        if text_len > 100:
            ok += 1
            status = f"OK ({text_len}자)"
        else:
            no_content += 1
            status = f"본문없음 ({text_len}자)"
    except Exception as ex:
        fail += 1
        status = f"오류: {ex}"
    print(f"  [{p['log_no']}] {p['title']} → {status}")

print(f"\n결과: 성공 {ok}/10  본문없음 {no_content}/10  오류 {fail}/10")
