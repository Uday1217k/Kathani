import os
import json
import datetime
from google import genai
from google.genai import types
import yagmail

# --- STABILIZATION FIX ---
# We explicitly set api_version to 'v1' to bypass the deprecated 'v1beta' endpoint.
client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"],
    http_options={'api_version': 'v1'}
)

def get_next_genre():
    with open('genre.json', 'r') as f:
        genres = json.load(f)
    with open('today_genre.json', 'r') as f:
        today = json.load(f)
    
    next_index = (today['last_index'] % 7) + 1
    genre_name = genres[str(next_index)]
    
    today['last_index'] = next_index
    today['last_run'] = str(datetime.date.today())
    with open('today_genre.json', 'w') as f:
        json.dump(today, f)
    
    return genre_name

def generate_content(genre):
    # Using Search Grounding to find fresh inspiration
    prompt = (f"Search for unique, trending story prompts in the {genre} genre. "
              f"Based on your findings, write a high-quality short story with a unique title. "
              f"Format: TITLE: [Title] CONTENT: [Story Content]")
    
    # Note: Use types.GoogleSearch() for the stable v1 API
    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )
    )
    
    # In the new SDK, response.text is the correct way to access the string
    return response.text

def save_and_email(genre, raw_text):
    # Parsing with safety fallback
    try:
        if "CONTENT:" in raw_text:
            title = raw_text.split("CONTENT:")[0].replace("TITLE:", "").strip()
            content = raw_text.split("CONTENT:")[1].strip()
        else:
            title = f"A Daily {genre} Tale"
            content = raw_text
    except (IndexError, ValueError):
        title = f"A Daily {genre} Tale"
        content = raw_text

    date_str = str(datetime.date.today())
    
    # Auto-folder creation logic
    folder_path = f"stories/{genre}"
    os.makedirs(folder_path, exist_ok=True)
    
    # Save the Markdown file
    with open(f"{folder_path}/{date_str}.md", "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n**Genre: {genre}**\n**Date: {date_str}**\n\n{content}")

    # Load Email Template
    with open('email_body.html', 'r', encoding="utf-8") as f:
        template = f.read()
    
    html_content = template.replace("{{TITLE}}", title).replace("{{CONTENT}}", content).replace("{{GENRE}}", genre)
    
    # Email Dispatch using Secrets
    # Ensure your YAML matches these environment variable names!
    user_email = os.environ.get("EMAIL_ID") or os.environ.get("EMAIL_USER")
    user_pass = os.environ.get("EMAIL_PASSWORD") or os.environ.get("EMAIL_PASS")
    
    yag = yagmail.SMTP(user_email, user_pass)
    yag.send(to=user_email, subject=f"Project Kathani: {title}", contents=html_content)

if __name__ == "__main__":
    current_genre = get_next_genre()
    story_data = generate_content(current_genre)
    save_and_email(current_genre, story_data)
