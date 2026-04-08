import os
import json
import datetime
from google import genai
import yagmail

# --- STABILITY UPDATE ---
# Removed http_options and forced versioning to let the SDK 
# choose the best working endpoint for your region.
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
    # We will use a more descriptive prompt to replace the search tool
    prompt = (f"Act as a professional author. Write a creative, unique short story in the {genre} genre "
              f"that would appeal to modern readers. "
              f"Structure your response exactly like this:\n"
              f"TITLE: [Your Story Title]\n"
              f"CONTENT: [The full story text]")
    
    # Standard generation - no 'tools' or 'config' to avoid 400/404 errors
    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents=prompt
    )
    return response.text

def save_and_email(genre, raw_text):
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
    folder_path = os.path.join("stories", genre)
    os.makedirs(folder_path, exist_ok=True)
    
    file_path = os.path.join(folder_path, f"{date_str}.md")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n**Genre: {genre}**\n**Date: {date_str}**\n\n{content}")

    try:
        with open('email_body.html', 'r', encoding="utf-8") as f:
            template = f.read()
        
        html_content = template.replace("{{TITLE}}", title).replace("{{CONTENT}}", content).replace("{{GENRE}}", genre)
        
        user_email = os.environ["EMAIL_USER"]
        user_pass = os.environ["EMAIL_PASS"]
        
        yag = yagmail.SMTP(user_email, user_pass)
        yag.send(to=user_email, subject=f"Project Kathani: {title}", contents=html_content)
        print(f"Success! {genre} story created.")
    except Exception as e:
        print(f"File saved, but email failed: {e}")

if __name__ == "__main__":
    current_genre = get_next_genre()
    story_data = generate_content(current_genre)
    save_and_email(current_genre, story_data)
