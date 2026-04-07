import os
import json
import datetime
import google.generativeai as genai
import yagmail

# Setup Gemini
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

def get_next_genre():
    with open('genre.json', 'r') as f:
        genres = json.load(f)
    with open('today_genre.json', 'r') as f:
        today = json.load(f)
    
    next_index = (today['last_index'] % 7) + 1
    genre_name = genres[str(next_index)]
    
    # Update today_genre.json
    today['last_index'] = next_index
    today['last_run'] = str(datetime.date.today())
    with open('today_genre.json', 'w') as f:
        json.dump(today, f)
    
    return genre_name

def generate_content(genre):
    # Using Gemini's built-in search tool capabilities for ideas
    model = genai.GenerativeModel(
        model_name='gemini-1.5-flash',
        tools=[{"google_search_retrieval": {}}]
    )
    
    prompt = f"Search for unique, trending story prompts or news in the {genre} genre. Based on findings, write a high-quality short story with a unique title. Format the output as: TITLE: [Title] CONTENT: [Story Content]"
    
    response = model.generate_content(prompt)
    return response.text

def save_and_email(genre, raw_text):
    title = raw_text.split("CONTENT:")[0].replace("TITLE:", "").strip()
    content = raw_text.split("CONTENT:")[1].strip()
    date_str = str(datetime.date.today())
    
    # Save as Markdown
    path = f"stories/{genre}/{date_str}.md"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(f"# {title}\n\n**Genre: {genre}**\n**Date: {date_str}**\n\n{content}")

    # Send Email
    with open('email_body.html', 'r') as f:
        template = f.read()
    
    html_content = template.replace("{{TITLE}}", title).replace("{{CONTENT}}", content).replace("{{GENRE}}", genre)
    
    yag = yagmail.SMTP(os.environ["EMAIL_USER"], os.environ["EMAIL_PASS"])
    yag.send(to=os.environ["RECEIVER_EMAIL"], subject=f"Kathani Daily: {title}", contents=html_content)

if __name__ == "__main__":
    current_genre = get_next_genre()
    story_data = generate_content(current_genre)
    save_and_email(current_genre, story_data)
