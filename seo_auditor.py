```python
import requests
from bs4 import BeautifulSoup
import re
import json
import time
import google.generativeai as genai
from collections import Counter
from urllib.parse import urlparse

# --- CONFIGURATION ---
# The environment provides the API key automatically
API_KEY = "" 
genai.configure(api_key=API_KEY)

class AISEOAuditor:
    def __init__(self, url):
        self.url = url
        self.domain = urlparse(url).netloc
        self.raw_html = ""
        self.soup = None
        self.report = {
            "metadata": {},
            "headers": {},
            "images": {"total": 0, "missing_alt": 0},
            "content": {"word_count": 0, "top_keywords": []},
            "score": 0,
            "ai_suggestions": ""
        }

    def fetch_page(self):
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get(self.url, headers=headers, timeout=15)
            response.raise_for_status()
            self.raw_html = response.text
            self.soup = BeautifulSoup(self.raw_html, 'html.parser')
            return True
        except Exception as e:
            print(f"Error fetching URL: {e}")
            return False

    def scrape_data(self):
        if not self.soup: return

        # Meta Tags
        title_tag = self.soup.find('title')
        self.report["metadata"]["title"] = title_tag.string.strip() if title_tag else "Missing"
        
        desc_tag = self.soup.find('meta', attrs={'name': 'description'})
        self.report["metadata"]["description"] = desc_tag['content'].strip() if desc_tag else "Missing"

        # Headers
        for i in range(1, 7):
            tags = self.soup.find_all(f'h{i}')
            self.report["headers"][f"h{i}"] = [t.get_text().strip() for t in tags]

        # Images
        imgs = self.soup.find_all('img')
        self.report["images"]["total"] = len(imgs)
        self.report["images"]["missing_alt"] = len([img for img in imgs if not img.get('alt')])

        # Content Analysis
        text = self.soup.get_text()
        words = re.findall(r'\w+', text.lower())
        self.report["content"]["word_count"] = len(words)
        
        # Keyword density (excluding common stop words)
        stop_words = {'the', 'and', 'to', 'of', 'a', 'in', 'is', 'it', 'for', 'on', 'with', 'that', 'this'}
        filtered_words = [w for w in words if w not in stop_words and len(w) > 3]
        self.report["content"]["top_keywords"] = Counter(filtered_words).most_common(10)

    def calculate_base_score(self):
        score = 100
        meta = self.report["metadata"]
        
        if meta["title"] == "Missing": score -= 20
        elif len(meta["title"]) < 30 or len(meta["title"]) > 60: score -= 5
        
        if meta["description"] == "Missing": score -= 15
        elif len(meta["description"]) < 120: score -= 5
        
        if not self.report["headers"]["h1"]: score -= 15
        
        img_stats = self.report["images"]
        if img_stats["total"] > 0:
            missing_ratio = img_stats["missing_alt"] / img_stats["total"]
            score -= int(missing_ratio * 15)

        if self.report["content"]["word_count"] < 300: score -= 10
        
        self.report["score"] = max(0, score)

    def get_ai_analysis(self):
        """Uses Gemini 2.5 Flash to provide deep insights with retry logic."""
        model = genai.GenerativeModel('gemini-2.5-flash-preview-09-2025')
        
        prompt = f"""
        Act as a Senior SEO Expert. Analyze the following data for the website {self.url}:
        - Title: {self.report['metadata']['title']}
        - Description: {self.report['metadata']['description']}
        - H1 Headers: {self.report['headers']['h1']}
        - Top Keywords: {self.report['content']['top_keywords']}
        - Word Count: {self.report['content']['word_count']}
        - Images without Alt-text: {self.report['images']['missing_alt']} out of {self.report['images']['total']}

        Provide:
        1. 3 critical issues that hurt ranking.
        2. 3 quick wins for immediate improvement.
        3. A suggested optimized Meta Title and Description based on the top keywords.
        Keep the tone professional and actionable.
        """

        retries = 5
        for i in range(retries):
            try:
                response = model.generate_content(prompt)
                self.report["ai_suggestions"] = response.text
                return
            except Exception as e:
                if i < retries - 1:
                    time.sleep(2**i) # Exponential backoff
                else:
                    self.report["ai_suggestions"] = "AI Analysis temporarily unavailable. Please check your API configuration."

    def run_audit(self):
        print(f"🚀 Starting audit for: {self.url}...")
        if self.fetch_page():
            self.scrape_data()
            self.calculate_base_score()
            print("🧠 Running AI-driven intelligence analysis...")
            self.get_ai_analysis()
            return self.report
        return None

if __name__ == "__main__":
    target_url = input("Enter website URL to audit (include https://): ")
    auditor = AISEOAuditor(target_url)
    results = auditor.run_audit()

    if results:
        print("\n" + "="*50)
        print(f"SEO SCORE: {results['score']}/100")
        print("="*50)
        print(f"\n[METADATA]")
        print(f"Title: {results['metadata']['title']}")
        print(f"Description: {results['metadata']['description']}")
        
        print(f"\n[AI INSIGHTS]")
        print(results['ai_suggestions'])
        print("="*50)
    else:
        print("Audit failed. Check the URL and your connection.")

```
      
