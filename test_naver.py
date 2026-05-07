"""
네이버 블로그 크롤링 테스트
실행: python3 test_naver.py
"""
import requests
from bs4 import BeautifulSoup
import feedparser
import json

BLOG_ID = "9594jh"
RSS_URL = f"https://rss.blog.naver.com/{BLOG_ID}.xml"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://m.blog.naver.com/",
}


def test_rss():
    print("=== 1. RSS 포스트 목록 테스트 ===")
    feed = feedparser.parse(RSS_URL)
    if not feed.entries:
        print("  RSS 실패")
        return []

    print(f"  포스트 {len(feed.entries)}개 발견")
    posts = []
    for e in feed.entries[:3]:
        # RSS link → logNo 추출
        link = e.get("link", "")
        log_no = link.split("/")[-1].split("?")[0]
        posts.append({"title": e.title, "link": link, "log_no": log_no})
        print(f"  - [{log_no}] {e.title}")
    return posts


def test_mobile_fetch(log_no):
    print(f"\n=== 2. 모바일 본문 크롤링 테스트 (logNo={log_no}) ===")
    url = f"https://m.blog.naver.com/{BLOG_ID}/{log_no}"
    resp = requests.get(url, headers=HEADERS, timeout=10)
    print(f"  HTTP {resp.status_code}")
    if resp.status_code != 200:
        print("  실패")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # SmartEditor 3 (최신)
    content_div = soup.select_one("div.se-main-container")
    # 구형 에디터
    if not content_div:
        content_div = soup.select_one("div#postViewArea")
    # 다른 케이스
    if not content_div:
        content_div = soup.select_one("div.post_ct")

    if not content_div:
        print("  본문 div를 찾지 못했음")
        print("  사용 가능한 div class 목록:")
        for div in soup.find_all("div", class_=True)[:10]:
            print(f"    {div.get('class')}")
        return None

    text = content_div.get_text(separator="\n", strip=True)
    print(f"  본문 길이: {len(text)}자")
    print(f"  본문 앞 200자:\n{text[:200]}")
    return text


def test_category_list():
    print("\n=== 3. 카테고리별 포스트 목록 테스트 ===")
    # 카테고리 없이 전체 목록
    url = f"https://m.blog.naver.com/{BLOG_ID}?categoryNo=0&currentPage=1"
    resp = requests.get(url, headers=HEADERS, timeout=10)
    print(f"  HTTP {resp.status_code}")
    if resp.status_code != 200:
        return

    soup = BeautifulSoup(resp.text, "html.parser")
    posts = soup.select("a.item_title") or soup.select("strong.ell") or soup.select("a[class*='title']")
    print(f"  목록에서 찾은 포스트: {len(posts)}개")
    for p in posts[:5]:
        href = p.get("href", "")
        print(f"  - {p.get_text(strip=True)[:40]} | {href}")


if __name__ == "__main__":
    posts = test_rss()

    if posts:
        log_no = posts[0]["log_no"]
        test_mobile_fetch(log_no)
    else:
        # RSS 실패 시 직접 최근 포스트 시도 (logNo는 임의값 - 실제 번호로 바꿔야 함)
        print("\n  RSS 실패 → 카테고리 목록으로 시도")
        test_category_list()

    print("\n=== 테스트 완료 ===")
