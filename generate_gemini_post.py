import os
import datetime
import google.generativeai as genai
import sys
import random # <--- ADD THIS IMPORT
from dotenv import load_dotenv

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

# The prompt for Gemini
# You can customize this heavily!
# You could even read this from a file or another source.
PROMPT_TEMPLATE  = """
You are Gjergj Kastrioti, Skenderbe, write a daily blog post, it can be serious, fun or casual depending on the day (around 1000-2000 words) in Markdown format
about any interesting new development it may have happened back at his days.
Include a catchy title as an H1 heading (e.g., # My Awesome Title).
Do not include a "Published Date" or "Author" section, as the filename will handle the date.
Write it in albanian.
"""

# Output directory for the blog posts
OUTPUT_DIR = "blog/Memorje"
# Filename prefix (still useful as a fallback or part of the slug)
FILENAME_PREFIX = "skanderbeg-era-insight"

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

    if total_days_in_period < 0: # Should be caught by above, but good sanity check
        print("Error: Calculated negative days in Skanderbeg's lifespan.")
        sys.exit(1)
    if total_days_in_period == 0: # If birth and death are same day
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

    # Generate the random date for this post
    random_historical_date = get_random_date_in_skanderbeg_era()
    filename_date = random_historical_date.strftime("%Y-%m-%d")
    print(f"Generated random historical date for post: {filename_date}")

    # Format the prompt with the random date
    current_prompt = PROMPT_TEMPLATE.format(random_date_str=random_historical_date.strftime("%B %d, %Y"))

    print(f"Sending prompt to Gemini model ({MODEL_NAME}) for date {filename_date}...")
    # print(f"Prompt: {current_prompt[:200]}...") # Optional: print start of prompt for debugging

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

    # Create filename with the random historical date
    # Slugification remains the same
    try:
        first_line = generated_text.split('\n', 1)[0]
        if first_line.startswith("# "):
            title_slug = first_line.lstrip("# ").strip().lower().replace(" ", "-")
            title_slug = "".join(c for c in title_slug if c.isalnum() or c == '-')
            title_slug = "-".join(filter(None, title_slug.split("-")))
            filename = f"{filename_date}-{title_slug[:50]}.md"
        else:
            filename = f"{filename_date}-{FILENAME_PREFIX}.md"
    except Exception:
        filename = f"{filename_date}-{FILENAME_PREFIX}.md"

    filepath = os.path.join(OUTPUT_DIR, filename)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(generated_text)

    print(f"Blog post saved to: {filepath}")
    return filepath

if __name__ == "__main__":
    generated_file = generate_post()
    # This print is crucial for the GitHub Action to capture the filename
    print(f"::set-output name=generated_filepath::{generated_file}")


# It's best practice to load the API key from an environment variable





