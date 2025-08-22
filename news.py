from playwright.sync_api import sync_playwright
import json


def scrape_and_save():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://telugu.getlokalapp.com/andhra-news/ongole/ongole")

        # Scrape titles
        titles = [t.inner_text() for t in page.query_selector_all("h2")]

        browser.close()

    # Save to JSON
    data = {"news_titles": titles}
    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


    print("✅ Saved news.json and news.docx successfully!")

if __name__ == "__main__":
    scrape_and_save()
