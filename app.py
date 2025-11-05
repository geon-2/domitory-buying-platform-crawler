from flask import Flask, request, jsonify
from bs4 import BeautifulSoup as bs
import requests, asyncio
from playwright.async_api import async_playwright

app = Flask(__name__)

# ✅ 브라우저 기반 User-Agent (정상 모바일 크롬)
BROWSER_UA = (
    "Mozilla/5.0 (Linux; Android 11; Pixel 5) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/117.0.0.0 Mobile Safari/537.36"
)

headers = {
    "User-Agent": BROWSER_UA,
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}


# ✅ requests 방식 (빠른 시도)
def fetch_with_requests(url: str):
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = bs(resp.text, "html.parser")

        og_title = soup.select_one('meta[property="og:title"]')
        og_desc = soup.select_one('meta[property="og:description"]')
        og_img = soup.select_one('meta[property="og:image"]')

        if og_title and og_desc and og_img:
            return {
                "title": og_title.get("content"),
                "description": og_desc.get("content"),
                "image": og_img.get("content"),
            }
        else:
            return None
    except Exception:
        return None


# ✅ Playwright 방식 (JS 렌더링 포함, fallback)
async def fetch_with_playwright(url: str):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=BROWSER_UA,
                locale="ko-KR",
                viewport={"width": 390, "height": 844},
            )
            page = await context.new_page()
            await page.goto(url, wait_until="networkidle", timeout=20000)
            html = await page.content()
            soup = bs(html, "html.parser")

            og_title = soup.select_one('meta[property="og:title"]')
            og_desc = soup.select_one('meta[property="og:description"]')
            og_img = soup.select_one('meta[property="og:image"]')

            data = {
                "title": og_title.get("content") if og_title else None,
                "description": og_desc.get("content") if og_desc else None,
                "image": og_img.get("content") if og_img else None,
            }

            # 가격 정보 (옵션)
            try:
                data["original_price"] = (
                    soup.select_one(".original-price-amount").get_text(strip=True).replace("원", "")
                    if soup.select_one(".original-price-amount")
                    else None
                )
                data["discount_rate"] = (
                    soup.select_one(".original-price > :first-child > div").get_text(strip=True)
                    if soup.select_one(".original-price > :first-child > div")
                    else None
                )
                data["final_price"] = (
                    soup.select_one(".final-price-amount").get_text(strip=True).replace("원", "")
                    if soup.select_one(".final-price-amount")
                    else None
                )
            except Exception:
                pass

            await browser.close()
            return data
    except Exception as e:
        return {"error": str(e)}


@app.route("/")
def hello():
    return "Coupang Playwright crawler ✅"


@app.route("/crawling", methods=["GET"])
def crawling():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "url parameter required"}), 400

    # 1️⃣ requests 우선 시도
    data = fetch_with_requests(url)
    if data:
        return jsonify({"method": "requests", "data": data})

    # 2️⃣ 실패 시 Playwright fallback
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    data = loop.run_until_complete(fetch_with_playwright(url))
    if data:
        return jsonify({"method": "playwright", "data": data})
    else:
        return jsonify({"error": "Failed to fetch"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)