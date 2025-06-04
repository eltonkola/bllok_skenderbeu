import os
import datetime # For today's date in YAML
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

Mos përfshi një seksion të veçantë "Data e Publikimit" ose "Autori" në trupin e postimit,
pasi kjo do të trajtohet nga metadata e skedarit dhe titulli H1.
Përqendrohu në autenticitetin historik të përzier me rrëfim tërheqës.
Sigurohu që i gjithë teksti, përfshirë titullin, të jetë në shqip.
"""

OUTPUT_DIR = "blog/Memorje"
FILENAME_FALLBACK_BASE = "Kujtime Skenderbeut Pa Titull Specifik"
MODEL_NAME = "gemini-1.5-flash-latest"

# --- Helper Functions ---
def get_random_date_for_ai_context():
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
    if not text_part: return ""
    illegal_chars_pattern = r'[<>:"/\\|?*\x00-\x1F#]'
    sanitized = re.sub(illegal_chars_pattern, '', text_part)
    sanitized = re.sub(r'^\.+', '', sanitized)
    sanitized = " ".join(sanitized.split()).strip()
    if not sanitized or sanitized == "." or sanitized == "..":
        return FILENAME_FALLBACK_BASE
    return sanitized[:max_length].strip()

# --- Main Logic ---
def generate_post():
    print(f"Configuring Gemini with API Key ending in ...{API_KEY[-4:]}")
    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel(MODEL_NAME)
    except Exception as e:
        print(f"Error configuring Gemini or creating model: {e}"); sys.exit(1)

    date_for_ai_prompt_context = get_random_date_for_ai_context()
    date_for_ai_context_str = date_for_ai_prompt_context.strftime("%d %B, %Y")

    current_prompt = PROMPT_TEMPLATE.format(random_date_for_ai_context=date_for_ai_context_str)
    print(f"Sending prompt to Gemini ({MODEL_NAME}) with AI date context: '{date_for_ai_context_str}'...")

    try:
        response = model.generate_content(current_prompt)
        generated_text_from_ai = response.text # Store AI's raw response
    except Exception as e:
        print(f"Error during Gemini API call: {e}"); sys.exit(1)

    if not generated_text_from_ai: print("Error: Gemini returned an empty response."); sys.exit(1)
    print("Gemini response received.")

    filename_base = FILENAME_FALLBACK_BASE
    try:
        first_line_of_ai_text = generated_text_from_ai.split('\n', 1)[0]
        if first_line_of_ai_text.startswith("# "):
            h1_title_from_ai = first_line_of_ai_text.lstrip("# ").strip()
            print(f"Extracted H1 title from AI: '{h1_title_from_ai}'")
            if h1_title_from_ai:
                potential_filename_base = sanitize_for_filename(h1_title_from_ai)
                if potential_filename_base:
                    filename_base = potential_filename_base
                else:
                    print(f"Warning: AI H1 title ('{h1_title_from_ai}') became empty after sanitization. Using fallback filename.")
            else:
                print("Warning: AI H1 title was empty. Using fallback filename.")
        else:
            print("Warning: AI response did not start with an H1. Using fallback filename.")
    except Exception as e:
        print(f"Error processing AI title for filename: {e}. Using fallback filename.")

    filename = f"{filename_base}.md"
    filename = re.sub(r'\s+', ' ', filename).strip()
    filepath = os.path.join(OUTPUT_DIR, os.path.normpath(filename))

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # --- Prepare YAML front matter and final content ---
    todays_date_str = datetime.date.today().strftime("%Y-%m-%d")
    yaml_front_matter = f"""---
date: "{todays_date_str}"
---

"""
    # Combine YAML front matter with the AI's generated text
    final_content_to_write = yaml_front_matter + generated_text_from_ai

    if os.path.exists(filepath):
        print(f"Warning: File '{filepath}' already exists. It will be overwritten.")
        # Example for unique filenames (optional):
        # current_datetime = datetime.datetime.now()
        # timestamp_suffix = current_datetime.strftime("%Y%m%d-%H%M%S")
        # # Find the last dot for extension
        # name_part, ext_part = os.path.splitext(filename_base)
        # unique_filename_base = f"{name_part}-{timestamp_suffix}"
        # filename = f"{unique_filename_base}{ext_part if ext_part else '.md'}" # Ensure .md if base had no extension
        # filepath = os.path.join(OUTPUT_DIR, os.path.normpath(filename))
        # print(f"New unique filepath: '{filepath}'")


    with open(filepath, "w", encoding="utf-8") as f:
        f.write(final_content_to_write)
    print(f"Blog post saved to: {filepath}")
    return filepath

if __name__ == "__main__":
    generated_file = generate_post()
    print(f"::set-output name=generated_filepath::{generated_file}")
