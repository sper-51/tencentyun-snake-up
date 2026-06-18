##获取登录后的Cookies，供后续接口调用使用
from playwright.sync_api import sync_playwright
import json

COOKIES_FILE = "cookies.json"
LOGIN_URL = "https://cloud.tencent.com/login?s_url=https%3A%2F%2Fcloud.tencent.com%2Fact%2Fpro%2Fdouble12-2025%3FfromSource%3Dgwzcw.10216579.10216579.10216579%26utm_medium%3Dcpc%26utm_id%3Dgwzcw.10216579.10216579.10216579%26msclkid%3D9d471e943d2d142808a4771f328779e6"


def auto_rush_buy():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(LOGIN_URL)

        print("请扫描二维码登录...")

        page.wait_for_url(lambda url: "cloud.tencent.com/act/pro/" in url, timeout=0)
        page.wait_for_timeout(2000) 

        print("登录成功！")

        cookies = context.cookies()
        print("获取到的Cookies：")
        with open(COOKIES_FILE, "w",encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        print(f"Cookies 已保存到 {COOKIES_FILE}，浏览器即将关闭。")
        browser.close()

if __name__ == "__main__":
    auto_rush_buy()
        
