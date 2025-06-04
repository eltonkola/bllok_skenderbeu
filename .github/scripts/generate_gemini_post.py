import os
import datetime
import google.generativeai as genai
import sys
import random
from dotenv import load_dotenv
import locale # For month names, though AI might handle it

# --- Configuration ---
load_dotenv() # Load .env file if present (for local testing)

API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    print("Error: GEMINI_API_KEY environment variable not set.")
    print("Ensure it's set in your environment or in a .env file in the project root.")
    sys.exit(1)

# --- Skanderbeg's Lifespan ---
SKANDERBEG_BIRTH_YEAR = 1405
SKANDERBEG_BIRTH_MONTH = 1
SKANDERBEG_BIRTH_DAY = 1

SKANDERBEG_DEATH_YEAR = 1468
SKANDERBEG_DEATH_MONTH = 1
SKANDERBEG_DEATH_DAY = 17

# --- Updated PROMPT_TEMPLATE ---
PROMPT_TEMPLATE = """
Ti je Gjergj Kastrioti, Skënderbeu. Shkruaj një hyrje ditari për datën {random_date_for_ai_context}.
Postimi duhet të jetë rreth 1000-2000 fjalë, në format Markdown dhe i shkruar në gjuhën shqipe.
Mund të jetë serioz, argëtues ose i zakonshëm, duke reflektuar mbi çdo zhvillim interesant, ngjarje ose mendim nga epoka jote.

RRJESHTI I PARË I PËRGJIGJES TËNDE DUHET TË JETË NJË TITULL H1 i Markdown-it.
KY TITULL VETË DUHET TË PËRFSHIJË DATËN E HYRJES NË FORMË TË PLOTË (p.sh., muaji, dita, viti).
Për shembull, nëse hyrja është për 14 Shtator 1456, titulli mund të jetë:
# 14 Shtator, 1456: Një Ditë e Rëndësishme në Krujë
Ose një shembull tjetër:
# Ditari im, Korrik 7, 1448: Mendime mbi Aleancat e Reja

Mos përfshi një seksion të veçantë "Data e Publikimit" ose "Autori" në trupin e postimit,
pasi titulli H1 dhe emri i skedarit do ta trajtojnë këtë.
Përqendrohu në autenticitetin historik të përzier me rrëfim tërheqës.
Sigurohu që i gjithë teksti, përfshirë titullin, të jetë në shqip.
"""

# Output directory for the blog posts
OUTPUT_DIR = "blog/Memorje" # Your specified directory
# Filename prefix (fallback if title extraction fails badly)
FILENAME_PREFIX = "kujtime-skenderbeut" # Albanian prefix

# Gemini model configuration
MODEL_NAME = "gemini-1.5-flash-latest" # Or "gemini-pro"

# --- Helper Function for Random Date ---
def get_random_date_in_skanderbeg_era():
    start_date = datetime.date(SKANDERBEG_BIRTH_YEAR, SKANDERBEG_BIRTH_MONTH, SKANDERBEG_BIRTH_DAY)
    end_date = datetime.date(SKANDERBEG_DEATH_YEAR, SKANDERBEG_DEATH_MONTH, SKANDERBEG_DEATH_DAY)

    if start_date > end_date:
        print("Error: Skanderbeg's birth date is after his death date in configuration.")
        sys.exit(1)

    time_difference = end_date - start_date
    total_days_in_period = time_difference.days

    if total_days_in_period < 0:
        print("Error: Calculated negative days in Skanderbeg's lifespan.")
        sys.exit(1)
    if total_days_in_period == 0:
        return start_date

    random_number_of_days = random.randint(0, total_days_in_period)
    random_date = start_date + datetime.timedelta(days=random_number_of_days)
    return random_date

# --- Main Logic ---
def generate_post():
    print(f"Configuring Gemini with API Key ending in ...{API_KEY[-4:]}")
    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel(MODEL_NAME)
    except Exception as e:
        print(f"Error configuring Gemini or creating model: {e}")
        sys.exit(1)

    random_historical_date = get_random_date_in_skanderbeg_era()
    # This is for the YYYY-MM-DD part of the filename
    filename_date_prefix = random_historical_date.strftime("%Y-%m-%d")
    print(f"Generated random historical date for post: {filename_date_prefix}")

    # Try to set locale for Albanian month names if possible (OS dependent)
    # This helps format the date string passed to the AI.
    # Common Albanian locales: 'sq_AL.UTF-8', 'sq_AL', 'sq'
    # If these fail, it will use the system default, AI should still manage.
    albanian_locales = ['sq_AL.UTF-8', 'sq_AL', 'sq']
    current_locale_set = False
    for loc in albanian_locales:
        try:
            locale.setlocale(locale.LC_TIME, loc)
            current_locale_set = True
            print(f"Successfully set locale to {loc} for date formatting.")
            break
        except locale.Error:
            print(f"Warning: Locale {loc} not available.")
            continue
    if not current_locale_set:
        print("Warning: Could not set an Albanian locale. Date format for AI might use default month names.")


    # Format the date string to pass to the AI for context in the prompt
    # e.g., "14 Shtator, 1456" or "14 September, 1456" if locale fails
    date_for_ai_context = random_historical_date.strftime("%d %B, %Y")

    current_prompt = PROMPT_TEMPLATE.format(random_date_for_ai_context=date_for_ai_context)

    print(f"Sending prompt to Gemini model ({MODEL_NAME}) for date {filename_date_prefix}...")
    # print(f"Full Prompt for AI:\n{current_prompt}\n------------------") # For debugging the full prompt

    try:
        response = model.generate_content(current_prompt)
        generated_text = response.text
    except Exception as e:
        print(f"Error during Gemini API call: {e}")
        if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
            print(f"Prompt Feedback: {response.prompt_feedback}")
        if hasattr(response, 'candidates') and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, 'finish_reason') and candidate.finish_reason:
                    print(f"Candidate Finish Reason: {candidate.finish_reason}")
                if hasattr(candidate, 'safety_ratings') and candidate.safety_ratings:
                    print(f"Candidate Safety Ratings: {candidate.safety_ratings}")
        sys.exit(1)

    if not generated_text:
        print("Error: Gemini returned an empty response.")
        sys.exit(1)

    print("Gemini response received.")

    # --- Updated Filename Generation ---
    ai_generated_title_part = FILENAME_PREFIX # Fallback
    try:
        first_line = generated_text.split('\n', 1)[0]
        if first_line.startswith("# "):
            # Extract the text after "# "
            title_text_from_ai = first_line.lstrip("# ").strip()
            print(f"Extracted H1 title from AI: '{title_text_from_ai}'")

            if title_text_from_ai: # Ensure it's not empty
                # Clean for filename: lowercase, remove specific punctuation, remove spaces
                cleaned_title = title_text_from_ai.lower()
                # Define punctuation to remove (add more if needed)
                # Includes common Albanian quotes and standard punctuation
                punctuation_to_remove = [":", ",", ".", "'", '"', "!", "?", "(", ")", "“", "”", "‘", "’", "«", "»"]
                for punc in punctuation_to_remove:
                    cleaned_title = cleaned_title.replace(punc, "")

                # Replace spaces with nothing (no hyphens)
                cleaned_title = cleaned_title.replace(" ", "")
                # Remove any leading/trailing hyphens that might have formed if punctuation was next to space
                cleaned_title = cleaned_title.strip("-")

                # A final check to ensure it's somewhat alphanumeric,
                # but trying to be gentle with Albanian characters.
                # This will keep letters (including Albanian ones if system supports unicode) and numbers.
                final_slug_chars = []
                for char_val in cleaned_title:
                    if char_val.isalnum(): # isalnum should handle unicode letters
                        final_slug_chars.append(char_val)
                ai_generated_title_part = "".join(final_slug_chars)


                if not ai_generated_title_part: # If cleaning resulted in empty string
                    print("Warning: AI title became empty after cleaning, using default prefix.")
                    ai_generated_title_part = FILENAME_PREFIX
                else:
                    print(f"Cleaned title for filename: '{ai_generated_title_part}'")
            else:
                print("Warning: AI H1 title was empty after stripping '# '. Using default prefix.")
        else:
            print("Warning: AI response did not start with an H1 ('# '). Using default prefix for filename.")

    except Exception as e:
        print(f"Error processing AI title for filename: {e}. Using default prefix.")

    # Construct the filename: YYYY-MM-DD-cleanedaititle.md
    # Limit the length of the AI-generated part to keep filenames manageable
    filename = f"{filename_date_prefix}-{ai_generated_title_part[:80]}.md"

    filepath = os.path.join(OUTPUT_DIR, filename)

    # Create output directory if it doesn't exist (recursive)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(generated_text)

    print(f"Blog post saved to: {filepath}")
    return filepath

if __name__ == "__main__":
    generated_file = generate_post()
    # This print is crucial for the GitHub Action to capture the filename
    print(f"::set-output name=generated_filepath::{generated_file}")
