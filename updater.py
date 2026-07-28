import datetime
import os
import json
from supabase import create_client
from google import genai
import requests
import feedparser

# Hardcode the clean base URL directly so it never fails
SUPABASE_URL = "https://gprgdzahgyebsghbgoav.supabase.co"

# Explicitly define your keys with secure fallbacks
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdwcmdkemFoZ3llYnNnaGJnb2F2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4NTIzNDgzMywiZXhwIjoyMTAwODEwODMzfQ.2jziL8RHMIOtLMTfRUObb__ZkssawAzDWKhq5n7du4k"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or "AQ.Ab8RN6JaYYwDs24nR0MJERBCSJJyOK6gCDerZzTGOrj5q3dRIw"

# Initialize clients cleanly
supabase = create_client(SUPABASE_URL, SUPABASE_KEY.strip('"\' '))
client = genai.Client(api_key=GEMINI_API_KEY.strip('"\' '))

def fetch_rss_headlines(feed_url, max_items=3):
    # Pretend to be a real Chrome browser so Google/BBC doesn't block the request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    response = requests.get(feed_url, headers=headers)

    feed = feedparser.parse(response.content)

    headlines = []
    for entry in feed.entries[:max_items]:
        summary = getattr(entry, 'summary', '')
        headlines.append(f"Title: {entry.title}\nSummary: {summary}")
    return "\n\n".join(headlines)

def generate_and_store_content(feed_url, category_name):
    print(f"Fetching live {category_name} news...")
    news_text = fetch_rss_headlines(feed_url)
    
    if not news_text:
        print(f"No news found for {category_name}.")
        return

    prompt = f"""
    You are an expert civil services and competitive exam mentor (UPSC/SSC). 
    Analyze the following live news articles. Filter out all trivial, local, or non-exam-relevant news (ignore local crimes, celebrity updates, routine political rhetoric, or entertainment).
    Focus strictly on high-yield current affairs mapped to exam syllabi:
    - National/International Policies, Acts, and Governance
    - Economic indices, fiscal updates, and budgetary allocations
    - Science & Technology breakthroughs and Space missions
    - Environmental reports, treaties, and biodiversity
    - Constitutional developments, judiciary judgments, and International Relations (IR)

    Output a strict JSON object with two keys:
    1. "notes": A list of exactly 5 high-yield, two line exam-focused bulletin notes highlighting the core significance of the news.
    2. "quizzes": A list of exactly 5 multiple-choice questions testing critical conceptual or factual points suitable for competitive exams. Each question item must have:
       - "question": string
       - "options": list of 4 options
       - "correct_index": integer (0 to 3)
       - "explanation": string explaining the underlying concept from an exam perspective.

    Return ONLY valid JSON. Here is the news text:
    {news_text}
    """

    response = client.models.generate_content(
        model='gemini-3.6-flash',
        contents=prompt,
        config={"response_mime_type": "application/json"}
    )
    
    clean_text = response.text.replace("```json", "").replace("```", "").strip()
    data = json.loads(clean_text)

    for note in data["notes"]:
        supabase.table("current_affairs_notes").insert({
    "note_text": note, 
    "category": category_name,
    "date": str(datetime.date.today())  # <-- Add this line
        }).execute()

    for quiz in data["quizzes"]:
        supabase.table("daily_quizzes").insert({
            "question": quiz["question"],
            "options": quiz["options"],
            "correct_index": quiz["correct_index"],
            "explanation": quiz["explanation"],
            "category": category_name,
            "date": str(datetime.date.today())
        }).execute()

    print("Successfully published today's content to the database!")

if __name__ == "__main__":
    # Pass the actual RSS web links directly into the function
    generate_and_store_content("https://www.thehindu.com/news/national/feeder/default.rss", category_name="national")
    generate_and_store_content("https://feeds.bbci.co.uk/news/world/rss.xml", category_name="international")