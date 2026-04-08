import os
import json
import datetime
from google import genai
from google.genai import types
import yagmail

# Initialize Client with forced Stable v1 API
client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"],
    http_options={'api_version': 'v1'}
)

def get_next_genre():
    # Load genre lists and tracking data
    with open('genre.json', 'r') as f:
        genres = json.load(f)
    with open('today_genre.json', 'r') as f:
        today = json.load(f)
    
    # Cycle through 7 genres
    next_index = (today['last_index'] % 7) + 1
    genre_name = genres[str(next_index)]
    
    # Update tracker
    today['last_index'] = next_index
    today['last_run'] = str(datetime.date.today())
    with open('today_genre.json', 'w') as f:
        json.dump(today, f)
    
    return genre_name

def generate_content(genre):
    prompt = (f"Write a high-quality, professional short story in the {genre} genre. "
              f"Include a unique title. "
              f"Format the output exactly as: TITLE: [Title] CONTENT: [Story Content]")
    
    try:
        # Attempt generation with Google Search Grounding
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        return response.text
    except Exception as e:
        print(f"Search Grounding unavailable or syntax error: {e}")
        print("Switching to standard generation mode...")
        
        # Fallback: Standard generation (No tools) to prevent 400 Errors
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt
        )
        return response.text

def save_and_email(genre, raw_text):
    # Parse Title and Content
    try:
        if "CONTENT:" in raw_text:
            title = raw_text.split("CONTENT:")[0].replace("TITLE:", "").strip()
            content = raw_text.split("CONTENT:")[1].strip()
        else:
            title = f"A {genre} Tale"
            content = raw_text
    except:
        title = f"Daily {genre} Dispatch"
        content = raw_text

    date_str = str(datetime.date.today())
    
    # Archive the story in the repo
    folder_path = f"stories/{genre}"
    os.makedirs(folder_path, exist_ok=True)
    with open(f"{folder_path}/{date_str}.md", "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n**Genre: {genre}**\n**Date: {date_str}**\n\n{content}")

    # Prepare and Send Email
    try:
        with open('email_body.html', 'r', encoding="utf-8") as f:
            template = f.read()
        
        html_content = template.replace("{{TITLE}}", title).replace("{{CONTENT}}", content).replace("{{GENRE}}", genre)
        
        email_user = os.environ["EMAIL_USER"]
        email_pass = os.environ["EMAIL_PASS"]
        
        yag = yagmail.SMTP(email_user, email_pass)
        yag.send(to=email_user, subject=f"Project Kathani: {title}", contents=html_content)
        print("Email dispatched successfully.")
    except Exception as e:
        print(f"Email failed: {e}")

if __name__ == "__main__":
    current_genre = get_next_genre()
    story_data = generate_content(current_genre)
    save_and_email(current_genre, story_data)
