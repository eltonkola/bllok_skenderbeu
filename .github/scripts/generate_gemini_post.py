import os
import datetime
import google.generativeai as genai
import sys
import random # Still needed for AI context date
from dotenv import load_dotenv
import re

# --- Configuration ---
load_dotenv()

API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    print("Error: GEMINI_API_KEY environment variable not set.")
    sys.exit(1)

# --- Skanderbeg's Lifespan (ONLY for generating context for AI prompt) ---
SKANDERBEG_BIRTH_YEAR_CONTEXT = 1405
SKANDERBEG_BIRTH_MONTH_CONTEXT = 1
SKANDERBEG_BIRTH_DAY_CONTEXT = 1
SKANDERBEG_DEATH_YEAR_CONTEXT = 1468
SKANDERBEG_DEATH_MONTH_CONTEXT = 1
SKANDERBEG_DEATH_DAY_CONTEXT = 17

PROMPT_TEMPLATE = """
Ti je Gjergj Kastrioti, Skënderbeu. Shkruaj një hyrje ditari për datën {random_date_for_ai_context}.
Postimi duhet të jetë rreth 1000-2000 fjalë, në format Markdown dhe i shkruar plotësisht në gjuhën shqipe.
Mund të jetë serioz, argëtues ose i zakonshëm, duke reflektuar mbi çdo zhvillim interesant, ngjarje ose mendim nga epoka jote.

RRJESHTI I PARË I PËRGJIGJES TËNDE DUHET TË JETË NJË TITULL H1 i Markdown-it.
KY TITULL VETË DUHET TË PËRFSHIJË DATËN E HYRJES NË FORMË TË PLOTË (p.sh., dita, emri i muajit, viti).
Për shembull, nëse data e dhënë është "14 Shtator, 1456", titulli yt mund të jetë:
# 14 Shtator, 1456: Një Ditë e Rëndësishme në Krujë
Ose, nëse data e dhënë është "3 Nëntor, 1462", titulli yt mund të jetë:
# 3 Nëntor, 1462: Duke Udhëtuar Nëpër Malësinë e Veriut, Histori Rreth Zjarrit

Mos përfshi një seksion të veçantë "Data e Publikimit" ose "Autori" në trupin e postimit.
Përqendrohu në autenticitetin historik të përzier me rrëfim tërheqës.
Sigurohu që i gjithë teksti, përfshirë titullin, të jetë në shqip.
"""

OUTPUT_DIR = "blog/Memorje"
# This fallback will be the entire filename (before .md) if AI H1 fails
FILENAME_FALLBACK_BASE = "Kujtime Skenderbeut Pa Titull Specifik"
MODEL_NAME = "gemini-1.5-flash-latest"

# --- Helper Functions ---
def get_random_date_for_ai_context():
    """Generates a random date within Skanderbeg's era FOR AI PROMPT CONTEXT ONLY."""
    start_date = datetime.date(SKANDERBEG_BIRTH_YEAR_CONTEXT, SKANDERBEG_BIRTH_MONTH_CONTEXT, SKANDERBEG_BIRTH_DAY_CONTEXT)
    end_date = datetime.date(SKANDERBEG_DEATH_YEAR_CONTEXT, SKANDERBEG_DEATH_MONTH_CONTEXT, SKANDERBEG_DEATH_DAY_CONTEXT)
    if start_date > end_date: sys.exit("Error: Context birth date is after death date.")
    time_difference = end_date - start_date
    total_days_in_period = time_difference.days
    if total_days_in_period < 0: sys.exit("Error: Negative days in context lifespan.")
    if total_days_in_period == 0: return start_date
    random_number_of_days = random.randint(0, total_days_in_period)
    return start_date + datetime.timedelta(days=random_number_of_days)

def sanitize_for_filename(text_part, max_length=150):
    """
    Sanitizes a string to be a filename (or part of it).
    Removes strictly illegal characters for most OSes. Keeps spaces and most punctuation.
    """
    if not text_part:
        return ""
    
    # Characters definitely illegal in most OS filenames (incl. control chars, # from H1)
    # Also removing leading dots that can make hidden files on Unix-like systems.
    illegal_chars_pattern = r'[<>:"/\\|?*\x00-\x1F#]'
    sanitized = re.sub(illegal_chars_pattern, '', text_part)
    
    # Remove leading dots from the whole string
    sanitized = re.sub(r'^\.+', '', sanitized)

    # Normalize multiple spaces to one, strip leading/trailing
    sanitized = " ".join(sanitized.split()).strip()
    
    # If after sanitization it's empty or just dots, return a fallback or handle
    if not sanitized or sanitized == "." or sanitized == "..":
        return FILENAME_FALLBACK_BASE # Or raise an error

    # Truncate if too long (consider the .md extension adds 3 chars)
    return sanitized[:max_length].strip()

# --- Main Logic ---
def generate_post():
    print(f"Configuring Gemini with API Key ending in ...{API_KEY[-4:]}")
    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel(MODEL_NAME)
    except Exception as e:
        print(f"Error configuring Gemini or creating model: {e}"); sys.exit(1)

    # Date for providing context to AI prompt (not used in filename directly)
    date_for_ai_prompt_context = get_random_date_for_ai_context()
    date_for_ai_context_str = date_for_ai_prompt_context.strftime("%d %B, %Y") # Uses system's default locale

    current_prompt = PROMPT_TEMPLATE.format(random_date_for_ai_context=date_for_ai_context_str)
    print(f"Sending prompt to Gemini ({MODEL_NAME}) with AI date context: '{date_for_ai_context_str}'...")

    try:
        response = model.generate_content(current_prompt)
        generated_text = response.text
    except Exception as e:
        print(f"Error during Gemini API call: {e}"); sys.exit(1)

    if not generated_text: print("Error: Gemini returned an empty response."); sys.exit(1)
    print("Gemini response received.")

    # --- Filename Generation ---
    filename_base = FILENAME_FALLBACK_BASE # Fallback for the entire filename base

    try:
        first_line = generated_text.split('\n', 1)[0]
        if first_line.startswith("# "):
            h1_title_from_ai = first_line.lstrip("# ").strip()
            print(f"Extracted H1 title from AI: '{h1_title_from_ai}'")

            if h1_title_from_ai:
                # The entire filename (before .md) comes from the sanitized H1 title
                potential_filename_base = sanitize_for_filename(h1_title_from_ai)
                if potential_filename_base: # Ensure it's not empty after sanitization
                    filename_base = potential_filename_base
                else:
                    print(f"Warning: AI H1 title ('{h1_title_from_ai}') became empty after sanitization. Using fallback filename.")
            else:
                print("Warning: AI H1 title was empty. Using fallback filename.")
        else:
            print("Warning: AI response did not start with an H1. Using fallback filename.")
    except Exception as e:
        print(f"Error processing AI title for filename: {e}. Using fallback filename.")

    # Construct the filename: "Sanitized AI H1 Title.md"
    filename = f"{filename_base}.md"
    # Final cleanup of multiple spaces (should be handled by sanitize_for_filename but good for safety)
    filename = re.sub(r'\s+', ' ', filename).strip()


    filepath = os.path.join(OUTPUT_DIR, filename)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # --- Check for existing file with the same name ---
    # This is important if the AI generates the exact same title on different days.
    # You might want to append a counter or a timestamp if it exists.
    # For now, it will overwrite.
    if os.path.exists(filepath):
        print(f"Warning: File '{filepath}' already exists. It will be overwritten.")
        # Example of appending a timestamp to make it unique:
        # timestamp = datetime.datetime.now().strftime("%H%M%S")
        # filename_base_unique = f"{filename_base} {timestamp}"
        # filename = f"{filename_base_unique}.md"
        # filepath = os.path.join(OUTPUT_DIR, filename)
        # print(f"New unique filepath: '{filepath}'")


    with open(filepath, "w", encoding="utf-8") as f:
        f.write(generated_text)
    print(f"Blog post saved to: {filepath}")
    return filepath

if __name__ == "__main__":
    generated_file = generate_post()
    print(f"::set-output name=generated_filepath::{generated_file}")
