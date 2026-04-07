import os
import json
import datetime
import google.generativeai as genai
import yagmail

# Setup Gemini
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

def get_next_genre():
    # Load the mapping and the state
    with open('genre.json', 'r') as f:
        genres = json.load(f)
    with open('today_genre.json', 'r') as f:
        today = json.load(f)
    
    # Logic: 1 to 7 cycle
    next_index = (today['last_index'] % 7) + 1
    genre_name = genres[str(next_index)]
    
    # Update memory for tomorrow
    today['last_index'] = next_index
    today['last_run'] = str(datetime.date.today())
    with open('today_genre.json', 'w') as f:
        json.dump(today, f)
    
    return genre_name

def generate_content(genre):
    # Gemini 1.5 Flash with Search capability
    model = genai.GenerativeModel(
        model_name='gemini-1.5-flash',
        tools=[{"google_search_retrieval": {}}]
    )
    
    prompt = (f"Search for unique, trending story prompts in the {genre} genre. "
              f"Write a professional short story with a unique title. "
              f"Output format: TITLE: [Title] CONTENT: [Story Content]")
    
    response = model.generate_content(prompt)
    return response.text

def save_and_email(genre, raw_text):
    # Parsing Title and Body
    try:
        title = raw_text.split("CONTENT:")[0].replace("TITLE:", "").strip()
        content = raw_text.split("CONTENT:")[1].strip()
    except IndexError:
        title = f"A {genre} Tale"
        content = raw_text

    date_str = str(datetime.date.today())
    
    # --- AUTO-FOLDER GENERATION ---
    # os.makedirs with exist_ok=True checks if folder exists; if not, it creates it.
    folder_path = f"stories/{genre}"
    os.makedirs(folder_path, exist_ok=True)
    
    file_path = f"{folder_path}/{date_str}.md"
    with open(file_path, "w") as f:
        f.write(f"# {title}\n\n**Genre: {genre}**\n**Date: {date_str}**\n\n{content}")

    # --- EMAIL DISPATCH ---
    with open('email_body.html', 'r') as f:
        template = f.read()
    
    html_content = template.replace("{{TITLE}}", title).replace("{{CONTENT}}", content).replace("{{GENRE}}", genre)
    
    # Using EMAIL_USER for both sender and receiver
    email_id = os.environ["EMAIL_ID"]
    email_password = os.environ["EMAIL_PASSWORD"]
    
    yag = yagmail.SMTP(email_id, email_password)
    yag.send(
        to=email_id, 
        subject=f"Project Kathani | {genre}: {title}", 
        contents=html_content
    )
    print(f"Successfully archived and sent: {title}")

if __name__ == "__main__":
    current_genre = get_next_genre()
    story_data = generate_content(current_genre)
    save_and_email(current_genre, story_data)
