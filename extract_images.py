import os
import sys
import time
import random
from pathlib import Path
from google import genai
from google.genai import types

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from settings import require_env

# 1. SETUP
API_KEY = require_env("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

# 2. UPDATED MODEL ID (April 27, 2026 Version)
# Note: Google transitioned 'gemini-3.1-flash-lite-preview' to the workhorse role this month.
MODEL_ID = "gemini-3.1-flash-lite-preview" 

IMAGE_FOLDER = r"C:\Projects\ollaa\data\images\telegram"
OUTPUT_FOLDER = r"C:\Projects\ollaa\data\extracted_text"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def check_models():
    """Diagnostic: Prints what your key can actually see to avoid 404s."""
    print("--- VERIFYING API ACCESS ---")
    try:
        available = [m.name for m in client.models.list() if "generateContent" in m.supported_methods]
        print(f"Your key sees: {available}")
        if f"models/{MODEL_ID}" not in available and MODEL_ID not in available:
            print(f"WARNING: {MODEL_ID} not found in your list. Use one from the list above.")
    except Exception as e:
        print(f"Could not list models: {e}")

def run_extraction():
    images = [f for f in os.listdir(IMAGE_FOLDER) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    print(f"Starting extraction for {len(images)} images using {MODEL_ID}...")

    for img_name in images:
        txt_path = os.path.join(OUTPUT_FOLDER, img_name.rsplit('.', 1)[0] + ".txt")
        
        # RESUME LOGIC
        if os.path.exists(txt_path):
            continue

        img_path = os.path.join(IMAGE_FOLDER, img_name)
        
        # Exponential Backoff for 503/429 errors
        for attempt in range(5):
            try:
                with open(img_path, "rb") as f:
                    image_bytes = f.read()

                response = client.models.generate_content(
                    model=MODEL_ID,
                    contents=[
                        types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                        "Extract all text. Focus on Location, Price, and Area."
                    ]
                )

                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(response.text.strip())
                
                print(f"Success: {img_name}")
                time.sleep(2) # Mandatory cooldown for free tier
                break 

            except Exception as e:
                err = str(e)
                if "503" in err or "429" in err:
                    wait = (2 ** attempt) + random.random()
                    print(f"Server busy on {img_name}. Retrying in {wait:.1f}s...")
                    time.sleep(wait)
                elif "404" in err:
                    print(f"FATAL: {MODEL_ID} is invalid. Run check_models().")
                    return
                else:
                    print(f"Error on {img_name}: {e}")
                    break

if __name__ == "__main__":
    check_models()
    run_extraction()