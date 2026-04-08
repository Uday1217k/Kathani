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
    # Files are now in the same directory as the script
    with open('genre.json', 'r') as f:
        genres = json.load(f)
    with open('today_genre.json', 'r') as f:
        today = json.load(f)
    
    # Cycle through genres (1-7)
    next_index = (today['last_index'] % 7) + 1
    genre_name = genres[str(next_index)]
    
    # Update memory
    today['last_index'] = next_index
    today['last_run'] = str(datetime.date.today())
    with open('today_genre.json', 'w') as f:
        json.dump(today, f)
    
    return genre_name

def generate_content(genre):
    prompt = (f"Write a high-quality short story in the {genre} genre. "
              f"Include a unique title. "
              f"Format: TITLE: [Title] CONTENT: [Story Content]")
    
    try:
        # Attempt with Search Grounding
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        return response.text
    except Exception as e:
        print(f"Grounding failed: {e}. Falling back to standard generation.")
        # Fallback to prevent 400 errors
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt
        )
        return response.text

def save_and_email(genre, raw_text):
    # Parse Title and Content
    try:
        if "CONTENT:" in raw_text:
            parts = raw_text.split("CONTENT:")
            title = parts[0].replace("TITLE:", "").strip()
            content = parts[1].strip()
        else:
            title = f"The {genre} Chronicles"
            content = raw_text
    except:
        title = f"Daily {genre} Dispatch"
        content = raw_text

    date_str = str(datetime.date.today())
    
    # Save to the 'stories/' directory as per your structure
    folder_path = os.path.join("stories", genre)
    os.makedirs(folder_path, exist_ok=True)
    
    file_path = os.path.join(folder_path, f"{date_str}.md")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n**Genre: {genre}**\n**Date: {date_str}**\n\n{content}")

    # Email Dispatch
    try:
        with open('email_body.html', 'r', encoding="utf-8") as f:
            template = f.read()
        
        html_content = template.replace("{{TITLE}}", title).replace("{{CONTENT}}", content).replace("{{GENRE}}", genre)
        
        # Use existing environment variable names from your workflow
        user_email = os.environ["EMAIL_USER"]
        user_pass = os.environ["EMAIL_PASS"]
        
        yag = yagmail.SMTP(user_email, user_pass)
        yag.send(to=user_email, subject=f"Project Kathani: {title}", contents=html_content)
        print(f"Success: {genre} story dispatched and archived.")
    except Exception as e:
        print(f"Email error: {e}")

if __name__ == "__main__":
    current_genre = get_next_genre()
    story_data = generate_content(current_genre)
    save_and_email(current_genre, story_data)
