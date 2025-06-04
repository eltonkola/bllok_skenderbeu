import os
import datetime
import google.generativeai as genai
import sys
import random
from dotenv import load_dotenv
import locale # Crucial for Albanian month names in strftime
import re
import dateparser # For parsing dates from AI text

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

# --- Updated PROMPT_TEMPLATE ---
# Emphasize Albanian date format in the H1 example more clearly.
PROMPT_TEMPLATE = """
Ti je Gjergj Kastrioti, Skënderbeu. Shkruaj një hyrje ditari për datën {random_date_for_ai_context_albanian}.
Postimi duhet të jetë rreth 1000-2000 fjalë, në format Markdown dhe i shkruar plotësisht në gjuhën shqipe.
Mund të jetë serioz, argëtues ose i zakonshëm, duke reflektuar mbi çdo zhvillim interesant, ngjarje ose mendim nga epoka jote.

RRJESHTI I PARË I PËRGJIGJES TËNDE DUHET TË JETË NJË TITULL H1 i Markdown-it.
KY TITULL VETË DUHET TË PËRFSHIJË DATËN E HYRJES NË FORMË TË PLOTË SHQIP (dita, emri i muajit në shqip, viti).
Për shembull, nëse data e dhënë është "14 Shtator, 1456", titulli yt mund të jetë:
# 14 Shtator, 1456: Një Ditë e Rëndësishme në Krujë
Ose, nëse data e dhënë është "3 Nëntor, 1462", titulli yt mund të jetë:
# 3 Nëntor, 1462: Duke Udhëtuar Nëpër Malësinë e Veriut, Histori Rreth Zjarrit

Mos përfshi një seksion të veçantë "Data e Publikimit" ose "Autori" në trupin e postimit.
Përqendrohu në autenticitetin historik të përzier me rrëfim tërheqës.
Sigurohu që i gjithë teksti, përfshirë titullin, të jetë në shqip.
"""

OUTPUT_DIR = "blog/Memorje"
FILENAME_TITLE_FALLBACK = "Kujtime Skenderbeut"
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

def sanitize_filename_part(text_part, max_length=80):
    if not text_part: return ""
    illegal_chars_pattern = r'[<>:"/\\|?*\x00-\x1F#]' # Added # as it's part of H1
    sanitized = re.sub(illegal_chars_pattern, '', text_part)
    sanitized = " ".join(sanitized.split()).strip()
    return sanitized[:max_length].strip()

# --- Main Logic ---
def generate_post():
    print(f"Configuring Gemini with API Key ending in ...{API_KEY[-4:]}")
    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel(MODEL_NAME)
    except Exception as e:
        print(f"Error configuring Gemini or creating model: {e}"); sys.exit(1)

    date_for_ai_prompt_context_obj = get_random_date_for_ai_context()
    
    # Attempt to set Albanian locale for strftime
    original_lc_time = locale.getlocale(locale.LC_TIME) # Store original
    date_for_ai_context_albanian_str = date_for_ai_prompt_context_obj.strftime("%d %B, %Y") # Default if locale fails

    # Common Albanian locales: 'sq_AL.UTF-8' (Linux), 'Albanian_Albania.1250' (Windows sometimes)
    # Or just 'sq' or 'sq_AL'
    albanian_locales_to_try = ['sq_AL.UTF-8', 'sq_AL', 'sq', 'Albanian_Albania.1250', 'Albanian']
    locale_set_successfully = False
    for loc_str in albanian_locales_to_try:
        try:
            locale.setlocale(locale.LC_TIME, loc_str)
            date_for_ai_context_albanian_str = date_for_ai_prompt_context_obj.strftime("%d %B, %Y")
            print(f"Successfully set locale to '{loc_str}'. AI date context: '{date_for_ai_context_albanian_str}'")
            locale_set_successfully = True
            break # Exit loop once a locale is successfully set
        except locale.Error:
            print(f"Warning: Locale '{loc_str}' not available.")
            continue
    
    if not locale_set_successfully:
        print(f"Warning: Could not set an Albanian locale. Using default system locale for AI date context: '{date_for_ai_context_albanian_str}'")

    # Crucially, reset locale to original after getting the string,
    # so it doesn't affect other parts of the script or other processes.
    locale.setlocale(locale.LC_TIME, original_lc_time)

    # Pass the (hopefully) Albanian formatted date string to the prompt
    current_prompt = PROMPT_TEMPLATE.format(random_date_for_ai_context_albanian=date_for_ai_context_albanian_str)
    print(f"Sending prompt to Gemini ({MODEL_NAME}) with AI date context: '{date_for_ai_context_albanian_str}'...")

    try:
        response = model.generate_content(current_prompt)
        generated_text = response.text
    except Exception as e:
        print(f"Error during Gemini API call: {e}"); sys.exit(1)

    if not generated_text: print("Error: Gemini returned an empty response."); sys.exit(1)
    print("Gemini response received.")

    filename_date_prefix = "UNDATED"
    filename_title_part_from_ai = FILENAME_TITLE_FALLBACK

    try:
        first_line = generated_text.split('\n', 1)[0]
        if first_line.startswith("# "):
            h1_title_from_ai = first_line.lstrip("# ").strip()
            print(f"Extracted H1 title from AI: '{h1_title_from_ai}'")

            if h1_title_from_ai:
                # Parse date from AI's H1. dateparser should handle Albanian month names.
                # Give 'sq' (Albanian) as a language hint.
                parsed_date_object = dateparser.parse(h1_title_from_ai, languages=['sq', 'en'], settings={'PREFER_DATES_FROM': 'past', 'STRICT_PARSING': False})
                
                title_text_for_filename = h1_title_from_ai

                if parsed_date_object:
                    filename_date_prefix = parsed_date_object.strftime("%Y-%m-%d")
                    print(f"Using date parsed from AI title for filename prefix: {filename_date_prefix}")
                    
                    # Attempt to remove the date part from the H1 to get the textual title
                    # This tries to find common separators.
                    separator_match = re.search(r'^(.{1,35}?)[\s]*[:\-–—][\s]*(.+)$', h1_title_from_ai) # Increased length for date part
                    title_after_separator_removal = h1_title_from_ai

                    if separator_match:
                        potential_date_str = separator_match.group(1).strip()
                        potential_title_str = separator_match.group(2).strip()
                        if dateparser.parse(potential_date_str, languages=['sq', 'en']): # Check if first part is a date
                            title_after_separator_removal = potential_title_str
                            print(f"Date part likely '{potential_date_str}', using title part: '{title_after_separator_removal}'")
                        else:
                            print(f"Part before separator ('{potential_date_str}') did not parse as date. Using full H1 for filename title part.")
                    else:
                        print(f"No clear 'Date: Title' separator found in AI H1. The filename title part might still include the date text.")
                    
                    title_text_for_filename = title_after_separator_removal
                else:
                    print(f"Warning: Could not parse date from AI H1 title ('{h1_title_from_ai}'). Using '{filename_date_prefix}' prefix.")
                
                filename_title_part_from_ai = sanitize_filename_part(title_text_for_filename)
            else:
                print("Warning: AI H1 title was empty. Using fallbacks.")
        else:
            print("Warning: AI response did not start with an H1. Using fallbacks.")
    except Exception as e:
        print(f"Error processing AI title for filename: {e}. Using fallbacks.")

    if not filename_title_part_from_ai:
        filename_title_part_from_ai = FILENAME_TITLE_FALLBACK

    filename = f"{filename_date_prefix} {filename_title_part_from_ai}.md"
    filename = re.sub(r'\s+', ' ', filename).strip()

    filepath = os.path.join(OUTPUT_DIR, filename)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(generated_text)
    print(f"Blog post saved to: {filepath}")
    return filepath

if __name__ == "__main__":
    generated_file = generate_post()
    print(f"::set-output name=generated_filepath::{generated_file}")
