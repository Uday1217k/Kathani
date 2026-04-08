import os
import json
import datetime
import requests
from bs4 import BeautifulSoup
from googlesearch import search
from google import genai
import yagmail

# --- Configuration ---
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

def get_web_inspiration(genre):
    """The Digital Scout: Scrapes the web for real-time prompt ideas."""
    query = f"latest {genre} short story writing prompts ideas"
    inspiration_text = ""
    print(f"Scraping the web for {genre} inspiration...")
    
    try:
        search_results = search(query, sleep_interval=2)
        urls = []
        for i, url in enumerate(search_results):
            urls.append(url)
            if i >= 2:  # Get top 3 URLs
                break

        for url in urls:
            try:
                response = requests.get(url, timeout=5)
                soup = BeautifulSoup(response.text, 'html.parser')
                meta = soup.find('meta', attrs={'name': 'description'})
                if meta:
                    inspiration_text += meta['content'] + " "
                else:
                    paragraphs = soup.find_all('p')
                    inspiration_text += " ".join([p.text for p in paragraphs[:2]]) + " "
                break
            except Exception:
                continue
    except Exception as e:
        print(f"Search failed, relying on internal creativity: {e}")
        
    return inspiration_text.strip() if inspiration_text else f"An unusual {genre} scenario."

def get_next_genre():
    if not os.path.exists('genre.json') or not os.path.exists('today_genre.json'):
        print("Configuration files missing! Returning default.")
        return "Fantasy"

    with open('genre.json', 'r') as f:
        genres = json.load(f)
    with open('today_genre.json', 'r') as f:
        today = json.load(f)
    
    next_index = (today['last_index'] % 7) + 1
    genre_name = genres.get(str(next_index), "Fantasy")
    
    today['last_index'] = next_index
    today['last_run'] = str(datetime.date.today())
    with open('today_genre.json', 'w') as f:
        json.dump(today, f)
    
    return genre_name

def generate_content(genre, inspiration):
    """The Master Storyteller: Prompts Gemini with strict constraints."""
    prompt = (
        f"Act as a professional author. Write a short story in the {genre} genre.\n"
        f"Use this scraped web concept as a loose inspiration seed: \"{inspiration}\"\n\n"
        "STRICT EDITORIAL RULES:\n"
        "1. Use basic, everyday English. Eradicate high vocabulary, dense metaphors, and confusing phrasal verbs.\n"
        "2. No AI hallucinations or non-sense words. Keep the plot logical and grounded.\n"
        "3. Give the story a 'tangy flavor'—make it engaging, lively, and include a clever twist!\n\n"
        "Structure your response EXACTLY with these four headings (do not bold the headings):\n"
        "TITLE: [Your Story Title]\n"
        "CHARACTERS: [List the characters and their relations, e.g., John (Brother), Mary (Sister)]\n"
        "BODY: [The full text of the story in simple paragraphs]\n"
        "CONCLUSION: [A clear ending or the final twist]"
    )
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    return response.text

def save_and_email(genre, raw_text):
    """The Archivist and Courier: Parses, saves, and dispatches."""
    # Carefully parsing the strict four-part structure
    try:
        title = raw_text.split("TITLE:")[1].split("CHARACTERS:")[0].strip()
        characters = raw_text.split("CHARACTERS:")[1].split("BODY:")[0].strip()
        body = raw_text.split("BODY:")[1].split("CONCLUSION:")[0].strip()
        conclusion = raw_text.split("CONCLUSION:")[1].strip()
    except IndexError:
        # Fallback if the AI slightly misbehaves on formatting
        title = f"The {genre} Chronicles"
        characters = "Unknown Cast"
        body = raw_text
        conclusion = "The End."

    date_str = str(datetime.date.today())
    folder_path = os.path.join("stories", genre)
    os.makedirs(folder_path, exist_ok=True)
    
    # 1. Save to Markdown Archive
    file_path = os.path.join(folder_path, f"{date_str}.md")
    with open(file_path, "w", encoding="utf-8") as f:
        md_content = (
            f"# {title}\n\n"
            f"**Genre:** {genre} | **Date:** {date_str}\n\n"
            f"### Characters\n{characters}\n\n"
            f"### The Story\n{body}\n\n"
            f"### Conclusion\n{conclusion}"
        )
        f.write(md_content)

    # 2. Prepare HTML Email
    # We replace the placeholders in your template with our beautifully parsed sections
    try:
        with open('email_body.html', 'r', encoding="utf-8") as f:
            template = f.read()
        
        # Formatting the text for HTML readability
        formatted_characters = characters.replace('\n', '<br>')
        formatted_body = body.replace('\n', '<br><br>')
        formatted_conclusion = conclusion.replace('\n', '<br>')
        
        # Combining them into the {{CONTENT}} block of your HTML
        combined_content = (
            f"<strong>Characters:</strong><br>{formatted_characters}<br><br>"
            f"<strong>The Story:</strong><br>{formatted_body}<br><br>"
            f"<strong>Conclusion:</strong><br>{formatted_conclusion}"
        )

        html_content = template.replace("{{TITLE}}", title).replace("{{CONTENT}}", combined_content).replace("{{GENRE}}", genre)
        
        # FIXED: Ensure we are using EMAIL_ID to match your GitHub Secrets!
        user_email = os.environ["EMAIL_ID"]
        user_pass = os.environ["EMAIL_PASSWORD"]
        
        yag = yagmail.SMTP(user_email, user_pass)
        yag.send(to=user_email, subject=f"Kathani Daily: {title} ({genre})", contents=html_content)
        print(f"Success! '{title}' has been archived and dispatched.")
    except Exception as e:
        print(f"File saved, but email failed: {e}")

if __name__ == "__main__":
    current_genre = get_next_genre()
    # Let the scout find inspiration first
    scraped_idea = get_web_inspiration(current_genre)
    # Pass both genre and inspiration to the storyteller
    story_data = generate_content(current_genre, scraped_idea)
    save_and_email(current_genre, story_data)
