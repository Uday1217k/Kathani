import os
import json
import datetime
from google import genai # New SDK import
from google.genai import types
import yagmail

# Setup Gemini with the new Client
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

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
    # Modern approach to Search (Grounding)
    prompt = (f"Search for unique, trending story prompts in the {genre} genre. "
              f"Write a professional short story with a unique title. "
              f"Output format: TITLE: [Title] CONTENT: [Story Content]")
    
    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearchRetrieval())]
        )
    )
    return response.text

def save_and_email(genre, raw_text):
    try:
        title = raw_text.split("CONTENT:")[0].replace("TITLE:", "").strip()
        content = raw_text.split("CONTENT:")[1].strip()
    except:
        title = f"The {genre} Chronicles"
        content = raw_text

    date_str = str(datetime.date.today())
    folder_path = f"stories/{genre}"
    os.makedirs(folder_path, exist_ok=True)
    
    with open(f"{folder_path}/{date_str}.md", "w") as f:
        f.write(f"# {title}\n\n**Genre: {genre}**\n**Date: {date_str}**\n\n{content}")

    with open('email_body.html', 'r') as f:
        template = f.read()
    
    html_content = template.replace("{{TITLE}}", title).replace("{{CONTENT}}", content).replace("{{GENRE}}", genre)
    
    email_id = os.environ["EMAIL_ID"]
    yag = yagmail.SMTP(email_id, os.environ["EMAIL_PASSWORD"])
    yag.send(to=email_id, subject=f"Project Kathani: {title}", contents=html_content)

if __name__ == "__main__":
    current_genre = get_next_genre()
    story_data = generate_content(current_genre)
    save_and_email(current_genre, story_data)
