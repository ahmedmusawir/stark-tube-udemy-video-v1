import os
import time
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from pydub import AudioSegment
import math

# --- Configuration ---
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SELECTED_SCRIPTS_DIR = Path("selected_scripts")
BASE_AUDIO_OUTPUT_DIR = Path("1-audio_gen/output_audio")

PROJECT_NAME = "coach-dashboard" 

# This path is now defined here for clarity.
PROJECT_AUDIO_OUTPUT_DIR = BASE_AUDIO_OUTPUT_DIR / PROJECT_NAME

CHUNK_LIMIT = 3500
WORDS_PER_SECOND_ESTIMATE = 2.5

# --- TTS Voice Instructions (Unchanged) ---
TTS_INSTRUCTIONS = """
Voice: Confident, dynamic, and charismatic, with a clear and compelling cadence that makes complex topics feel exciting and easy to understand. The voice should have a natural energy that builds anticipation.
Tone: Enthusiastic, knowledgeable, and forward-looking. It's the voice of someone who is passionate about the subject and genuinely wants the audience to share in the excitement of discovery. Avoids being dry or monotonous at all costs.
Dialect: Crisp, modern, and professional. The delivery is conversational, like a trusted expert talking directly to an intelligent friend.
Pronunciation: Flawlessly clear and precise. Key technical terms and brand names are articulated with authority. The pacing is deliberate, using short pauses to emphasize critical points and give the listener a moment to absorb the information.
Features: Uses a mix of upbeat, declarative statements and engaging, hypothetical questions ("What if you could...?"). The voice should naturally crescendo when revealing key insights and maintain a steady, engaging rhythm during explanations. This is the voice of a top-tier creator at the peak of their game.
"""

# --- Helper Functions (Unchanged) ---
def split_text(text: str, limit: int) -> list[str]:
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""
    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 < limit:
            current_chunk += para + "\n\n"
        else:
            chunks.append(current_chunk.strip())
            current_chunk = para + "\n\n"
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

def format_seconds_to_min_sec(seconds: float) -> str:
    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)
    time_str = ""
    if minutes > 0:
        time_str += f"{minutes} min "
    time_str += f"{remaining_seconds} sec"
    return time_str

# --- Main Synthesis Function ---
def synthesize_batch_scripts():
    print("\n--- Stark Audio Synthesis Prototype (Batch Mode) ---")

    if not SELECTED_SCRIPTS_DIR.exists():
        print(f"Error: Script directory '{SELECTED_SCRIPTS_DIR}' not found.")
        print("Please ensure '_selected_scripts' folder exists in the root.")
        return

    script_files = sorted([f for f in SELECTED_SCRIPTS_DIR.iterdir() if f.is_file() and f.suffix == '.txt'])
    if not script_files:
        print(f"No .txt script files found in '{SELECTED_SCRIPTS_DIR}'. Please place your scripts there.")
        return

    print("\nScripts found to be processed:")
    
    ### --- NEW: Accumulator for total estimated time --- ###
    total_estimated_seconds = 0.0

    for i, script_path in enumerate(script_files):
        try:
            content = script_path.read_text(encoding='utf-8')
            words = len(content.split())
            estimated_seconds = words / WORDS_PER_SECOND_ESTIMATE
            ### --- NEW: Add this script's time to the total --- ###
            total_estimated_seconds += estimated_seconds
            estimated_time_str = format_seconds_to_min_sec(estimated_seconds)
            print(f"  {i+1}. {script_path.name} --> {words} words --> {estimated_time_str}")
        except Exception as e:
            print(f"  {i+1}. Error reading {script_path.name}: {e}")

    ### --- NEW: Display the total estimated time --- ###
    formatted_total_time = format_seconds_to_min_sec(total_estimated_seconds)
    print("----------------------------------------------------------")
    print(f"Total Estimated Audio Length: {formatted_total_time}")
    print("----------------------------------------------------------")


    ### --- UPDATED: User verification with graceful exit --- ###
    prompt = "\nProceed with batch synthesis? (y/n, or 0 to exit): "
    proceed = input(prompt).lower().strip()

    if proceed == '0':
        print("Good bye, Tony.")
        return
    
    if proceed != 'y':
        print("Batch synthesis aborted by user.")
        return

    # This line ensures the output directory exists, creating it if necessary.
    PROJECT_AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\nOutput audio will be saved to: {PROJECT_AUDIO_OUTPUT_DIR}")

    total_files_processed = 0
    total_synthesis_time = 0.0

    print("\nStarting Batch Synthesis...")

    # --- Core Synthesis Loop (Unchanged) ---
    for i, script_path in enumerate(script_files):
        print(f"\n--- Processing {i+1}/{len(script_files)}: {script_path.name} ---")
        
        try:
            text_content = script_path.read_text(encoding="utf-8")
            words = len(text_content.split())
            estimated_seconds = words / WORDS_PER_SECOND_ESTIMATE
            estimated_time_str = format_seconds_to_min_sec(estimated_seconds)
            print(f"Now Processing: {script_path.name} --> {words} words --> {estimated_time_str} (estimated)")

            chunks = split_text(text_content, CHUNK_LIMIT)
            print(f"  Split into {len(chunks)} chunks.")

            combined_audio = AudioSegment.empty()
            synthesis_start_time = time.time()

            for j, chunk in enumerate(chunks):
                temp_chunk_path = PROJECT_AUDIO_OUTPUT_DIR / f"temp_chunk_{j+1}.mp3"
                with client.audio.speech.with_streaming_response.create(
                    model="gpt-4o-mini-tts",
                    voice="echo",
                    instructions=TTS_INSTRUCTIONS,
                    input=chunk
                ) as response:
                    response.stream_to_file(temp_chunk_path)
                
                combined_audio += AudioSegment.from_mp3(temp_chunk_path)
                os.remove(temp_chunk_path)

            actual_time_taken = time.time() - synthesis_start_time
            total_synthesis_time += actual_time_taken
            total_files_processed += 1
            
            output_audio_filename = script_path.stem + ".mp3"
            output_audio_path = PROJECT_AUDIO_OUTPUT_DIR / output_audio_filename

            combined_audio.export(output_audio_path, format="mp3")
            
            print(f"Done! [Audio File: {output_audio_path}]")
            print(f"Time Taken: {format_seconds_to_min_sec(actual_time_taken)}")

        except Exception as e:
            print(f"Error processing {script_path.name}: {e}")
            print("Skipping to next script...")

    print("\n----------------------------------------------------------")
    print("Batch Synthesis Complete!")
    print(f"Total files processed: {total_files_processed}")
    print(f"Total time spent synthesizing: {format_seconds_to_min_sec(total_synthesis_time)}")
    print("----------------------------------------------------------")

if __name__ == "__main__":
    synthesize_batch_scripts()