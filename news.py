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
        page.goto("https://telugu.getlokalapp.com/andhra-news/ongole/ongole")
        
        titles = [t.inner_text() for t in page.query_selector_all("h2")]
        
        browser.close()
    return titles

if __name__ == "__main__":
    try:
        titles = scrape_news()
        print(json.dumps({"success": True, "titles": titles}))
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
                              capture_output=True, text=True, timeout=30)
        
        # Clean up
        os.unlink(script_path)
        
        if result.returncode == 0:
            data = json.loads(result.stdout.strip())
            if data["success"]:
                return data["titles"]
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
        titles = run_scraper()
        
        return {
            "success": True,
            "city": "Ongole",
            "count": len(titles),
            "news": titles
        }
        
    except Exception as e:
        print(f"API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)