import os
import json
import datetime
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google import genai

# --- Configuration ---
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

def get_next_genre():
    """Reads the schedule and memory to determine today's genre."""
    if not os.path.exists('genre.json') or not os.path.exists('today_genre.json'):
        print("Configuration files missing! Returning default 'Fantasy'.")
        return "Fantasy"

    with open('genre.json', 'r') as f:
        genres = json.load(f)
    with open('today_genre.json', 'r') as f:
        today = json.load(f)
    
    # Cycles through days 1-7 safely
    next_index = (today['last_index'] % 7) + 1
    genre_name = genres.get(str(next_index), "Fantasy")
    
    today['last_index'] = next_index
    today['last_run'] = str(datetime.date.today())
    with open('today_genre.json', 'w') as f:
        json.dump(today, f)
    
    return genre_name

def generate_content(genre):
    """The Master Storyteller: Uses Native Google Search and includes Safety Nets."""
    print(f"Commissioning a {genre} story from Gemini...")
    
    prompt = (
        f"Act as a professional author. Write a short story in the {genre} genre.\n"
        f"FIRST, use your Google Search tool to find a unique '{genre} short story writing prompt' on the internet. "
        f"Then, use that prompt as the inspiration seed for your story.\n\n"
        "STRICT EDITORIAL RULES:\n"
        "1. Use basic, everyday English. Eradicate high vocabulary, dense metaphors, and confusing phrasal verbs.\n"
        "2. No AI hallucinations or non-sense words. Keep the plot logical and grounded.\n"
        "3. Give the story a 'tangy flavor'—make it engaging, lively, and include a clever twist!\n\n"
        "Structure your response EXACTLY with these four headings (do not bold the headings):\n"
        "TITLE: [Your Story Title]\n"
        "CHARACTERS: [List the characters and their relations]\n"
        "BODY: [The full text of the story in simple paragraphs]\n"
        "CONCLUSION: [A clear ending or the final twist]"
    )
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Utilizing the modern SDK with Native Search Activated
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config={'tools': [{'google_search': {}}]} 
            )
            
            # THE SAFETY SHIELD: Check if the AI's safety filter blocked the text
            if not response.text:
                print("Safety filter triggered. Response was empty.")
                return (
                    f"TITLE: The Censored {genre} Tale\n"
                    f"CHARACTERS: The Digital Censor\n"
                    f"BODY: Gemini attempted to write a {genre} story today, but it triggered Google's strict safety filters (likely due to action, violence, or sensitive themes). The narrative was blocked at the source.\n"
                    f"CONCLUSION: We shall try for a safer tale tomorrow."
                )
                
            return response.text
            
        except Exception as e:
            # Gracefully handle server traffic spikes (503) or rate limits (429)
            if '503' in str(e) or 'UNAVAILABLE' in str(e) or '429' in str(e):
                if attempt < max_retries - 1:
                    print(f"Gemini server is busy. Retrying in 30 seconds... (Attempt {attempt + 1} of {max_retries})")
                    time.sleep(30)
                else:
                    print("Max retries reached. The Gemini API is overwhelmed.")
                    return (
                        f"TITLE: The Silent {genre}\n"
                        f"CHARACTERS: The Automated Scribe\n"
                        f"BODY: The digital muses were overwhelmed today. The servers were too crowded to weave our daily tale.\n"
                        f"CONCLUSION: We shall try again tomorrow."
                    )
            else:
                print(f"An unexpected Gemini error occurred: {e}")
                return f"TITLE: A Technical Hitch\nCHARACTERS: None\nBODY: An unexpected error occurred: {e}\nCONCLUSION: End."

def save_and_email(genre, raw_text):
    """The Archivist and Courier: Parses the 4-part structure, saves, and emails using pure SMTP."""
    
    # THE FALLBACK: Ensure raw_text is never None before we try to split it
    if not raw_text:
        raw_text = (
            f"TITLE: The Missing {genre} Tale\n"
            f"CHARACTERS: Unknown\n"
            f"BODY: A fatal error occurred and the story text vanished before parsing.\n"
            f"CONCLUSION: End."
        )

    try:
        title = raw_text.split("TITLE:")[1].split("CHARACTERS:")[0].strip()
        characters = raw_text.split("CHARACTERS:")[1].split("BODY:")[0].strip()
        body = raw_text.split("BODY:")[1].split("CONCLUSION:")[0].strip()
        conclusion = raw_text.split("CONCLUSION:")[1].strip()
    except IndexError:
        # Fallback if the AI slightly alters the formatting
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

    # 2. Prepare and Send HTML Email via SMTP
    try:
        with open('email_body.html', 'r', encoding="utf-8") as f:
            template = f.read()
        
        # Format line breaks for HTML
        formatted_characters = characters.replace('\n', '<br>')
        formatted_body = body.replace('\n', '<br><br>')
        formatted_conclusion = conclusion.replace('\n', '<br>')
        
        combined_content = (
            f"<strong>Characters:</strong><br>{formatted_characters}<br><br>"
            f"<strong>The Story:</strong><br>{formatted_body}<br><br>"
            f"<strong>Conclusion:</strong><br>{formatted_conclusion}"
        )

        html_content = template.replace("{{TITLE}}", title).replace("{{CONTENT}}", combined_content).replace("{{GENRE}}", genre)
        
        user_email = os.environ["EMAIL_ID"]
        user_pass = os.environ["EMAIL_PASSWORD"]
        
        # Crafting the MIME Message
        msg = MIMEMultipart()
        msg['From'] = user_email
        msg['To'] = user_email
        msg['Subject'] = f"Kathani Daily: {title} ({genre})"
        msg.attach(MIMEText(html_content, 'html'))

        # Engaging the native SMTP server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(user_email, user_pass)
        server.send_message(msg)
        server.quit()
        
        print(f"Success! '{title}' has been safely archived and dispatched to your inbox via SMTP.")
    except Exception as e:
        print(f"File saved to repository, but email delivery failed: {e}")

if __name__ == "__main__":
    current_genre = get_next_genre()
    story_data = generate_content(current_genre)
    save_and_email(current_genre, story_data)
