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
import traceback

def scrape_news(district="prakasam"):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Construct URL dynamically based on district
            url = f"https://telugu.way2news.com/category/andhra-pradesh/{district}/"
            
            page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Wait for content to load
            page.wait_for_selector(".newsItem", timeout=15000)
            
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
                    continue
            
            browser.close()
            return news_items
    except Exception as e:
        raise e

if __name__ == "__main__":
    try:
        # Get district from command line arguments, default to prakasam
        district = sys.argv[1] if len(sys.argv) > 1 else "prakasam"
        news_data = scrape_news(district)
        result = {"success": True, "news": news_data}
        print(json.dumps(result))
    except Exception as e:
        error_result = {"success": False, "error": str(e), "traceback": traceback.format_exc()}
        print(json.dumps(error_result))
'''

def run_scraper(district="prakasam"):
    """Run the scraper in a separate process"""
    try:
        # Write scraper to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(SCRAPER_SCRIPT)
            script_path = f.name
        
        # Run the script with district parameter
        result = subprocess.run([sys.executable, script_path, district], 
                              capture_output=True, text=True, timeout=60)
        
        # Clean up
        os.unlink(script_path)
        
        print(f"Scraper stdout: {result.stdout}")
        print(f"Scraper stderr: {result.stderr}")
        print(f"Return code: {result.returncode}")
        
        if result.returncode == 0:
            stdout_clean = result.stdout.strip()
            if not stdout_clean:
                print("Empty stdout from scraper")
                return []
                
            try:
                data = json.loads(stdout_clean)
                if data.get("success") and data.get("news"):
                    return data["news"]
                else:
                    print(f"Scraper returned: {data}")
                    return []
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                print(f"Raw output: {repr(stdout_clean)}")
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
async def get_news(district: str = "prakasam"):
    try:
        print(f"Running scraper for district: {district}")
        news_data = run_scraper(district)
        
        return {
            "success": True,
            "district": district,
            "count": len(news_data),
            "news": news_data
        }
        
    except Exception as e:
        print(f"API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)