import json
import subprocess
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import tempfile
import os

app = FastAPI(title="Telugu News API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create your original scraper as a separate script
SCRAPER_SCRIPT = '''
from playwright.sync_api import sync_playwright
import json
import sys

def scrape_news():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://telugu.way2news.com/category/andhra-pradesh/prakasam/")
        
        # Wait for content to load
        page.wait_for_selector(".newsItem", timeout=10000)
        
        news_items = []
        news_elements = page.query_selector_all(".newsItem")
        
        for item in news_elements:
            try:
                # Extract headline and link
                headline_element = item.query_selector("h1 a")
                headline = headline_element.inner_text().strip() if headline_element else "No headline"
                news_link = headline_element.get_attribute("href") if headline_element else ""
                
                # Extract thumbnail image
                img_element = item.query_selector("figure img")
                thumbnail = img_element.get_attribute("src") if img_element else ""
                
                # Extract description
                desc_element = item.query_selector("p")
                description = desc_element.inner_text().strip() if desc_element else "No description"
                
                # Extract date if available
                date_element = item.query_selector("h6 span:last-child")
                date = date_element.inner_text().strip() if date_element else ""
                
                news_item = {
                    "headline": headline,
                    "description": description,
                    "thumbnail": thumbnail,
                    "news_link": news_link,
                    "date": date
                }
                
                news_items.append(news_item)
                
            except Exception as e:
                print(f"Error processing news item: {e}")
                continue
        
        browser.close()
        return news_items

if __name__ == "__main__":
    try:
        news_data = scrape_news()
        print(json.dumps({"success": True, "news": news_data}))
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
'''

def run_scraper():
    """Run the scraper in a separate process"""
    try:
        # Write scraper to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(SCRAPER_SCRIPT)
            script_path = f.name
        
        # Run the script
        result = subprocess.run([sys.executable, script_path], 
                              capture_output=True, text=True, timeout=60)
        
        # Clean up
        os.unlink(script_path)
        
        if result.returncode == 0:
            data = json.loads(result.stdout.strip())
            if data["success"]:
                return data["news"]
            else:
                print(f"Scraper error: {data['error']}")
                return []
        else:
            print(f"Subprocess error: {result.stderr}")
            return []
            
    except Exception as e:
        print(f"Error running scraper: {e}")
        return []

@app.get("/")
async def root():
    return {"message": "Telugu News API", "version": "1.0.0"}

@app.get("/api/news")
async def get_news():
    try:
        print("Running scraper in subprocess...")
        news_data = run_scraper()
        
        return {
            "success": True,
            "city": "Ongole",
            "count": len(news_data),
            "news": news_data
        }
        
    except Exception as e:
        print(f"API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)