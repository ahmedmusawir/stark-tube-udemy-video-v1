import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from pydub import AudioSegment
import math

# --- Configuration ---
# Load API key from .env file (ensure .env is in the project root)
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Define input and output directories relative to the script's location (project root)
SELECTED_SCRIPTS_DIR = Path("selected_scripts")
OUTPUT_AUDIO_DIR = Path("1-audio_gen/output_audio")

# Text chunk limit for OpenAI TTS (as per your existing code)
CHUNK_LIMIT = 3500

# --- TTS Voice Instructions ---
# These instructions guide the OpenAI TTS model's delivery
TTS_INSTRUCTIONS = """
Voice: Confident, dynamic, and charismatic, with a clear and compelling cadence that makes complex topics feel exciting and easy to understand. The voice should have a natural energy that builds anticipation.

Tone: Enthusiastic, knowledgeable, and forward-looking. It's the voice of someone who is passionate about the subject and genuinely wants the audience to share in the excitement of discovery. Avoids being dry or monotonous at all costs.

Dialect: Crisp, modern, and professional. The delivery is conversational, like a trusted expert talking directly to an intelligent friend.

Pronunciation: Flawlessly clear and precise. Key technical terms and brand names are articulated with authority. The pacing is deliberate, using short pauses to emphasize critical points and give the listener a moment to absorb the information.

Features: Uses a mix of upbeat, declarative statements and engaging, hypothetical questions ("What if you could...?"). The voice should naturally crescendo when revealing key insights and maintain a steady, engaging rhythm during explanations. This is the voice of a top-tier creator at the peak of their game.
"""

# --- Helper Function for Text Chunking ---
def split_text(text: str, limit: int) -> list[str]:
    """
    Splits a given text into chunks based on paragraph breaks,
    respecting a maximum character limit per chunk.
    """
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""
    for para in paragraphs:
        # Check if adding the current paragraph (plus two for potential newlines)
        # exceeds the limit.
        if len(current_chunk) + len(para) + 2 < limit:
            current_chunk += para + "\n\n"
        else:
            # If adding current paragraph exceeds limit, save current_chunk
            # and start a new one with the current paragraph.
            chunks.append(current_chunk.strip())
            current_chunk = para + "\n\n"
    
    # Add any remaining text as a final chunk
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

# --- Main Synthesis Function ---
def synthesize_single_script():
    """
    Prompts user for a script filename, synthesizes its audio,
    and saves it to the designated output folder.
    """
    print("\n--- Stark Audio Synthesis Prototype (Single File) ---")

    # Ensure the input script directory exists
    if not SELECTED_SCRIPTS_DIR.exists():
        print(f"Error: Script directory '{SELECTED_SCRIPTS_DIR}' not found.")
        print("Please ensure '_selected_scripts' folder exists in the root.")
        return

    # List available script files for user
    available_scripts = sorted([f.name for f in SELECTED_SCRIPTS_DIR.iterdir() if f.is_file() and f.suffix == '.txt'])
    if not available_scripts:
        print(f"No .txt script files found in '{SELECTED_SCRIPTS_DIR}'. Please place your scripts there.")
        return

    print("\nAvailable script files:")
    for i, script_name in enumerate(available_scripts):
        print(f"  {i+1}. {script_name}")

    # User input for filename
    # script_filename = input("\nEnter the script filename you want to synthesize (e.g., n8n_hosting_script_1.0.txt): ").strip()

    # script_path = SELECTED_SCRIPTS_DIR / script_filename

    # if not script_path.exists():
    #     print(f"Error: Script file '{script_filename}' not found in '{SELECTED_SCRIPTS_DIR}'.")
    #     return

    # --- User Selection Menu ---
    script_filename = None
    while script_filename is None:
        # The prompt is now smarter and includes the exit option.
        prompt = f"\nEnter a number to select a script (1-{len(available_scripts)}, or 0 to exit): "
        user_choice = input(prompt).strip()

        # 1. Handle graceful exit
        if user_choice == '0':
            print("Good bye, Tony.")
            return

        # 2. Handle selection by number
        try:
            choice_index = int(user_choice) - 1 # Convert to 0-based index
            if 0 <= choice_index < len(available_scripts):
                script_filename = available_scripts[choice_index]
                print(f"Selected: {script_filename}")
            else:
                # Handles numbers that are too high or too low
                print(f"Error: Invalid choice. Please select a number from the list.")
        except ValueError:
            # Handles non-numeric input
            print("Error: Invalid input. Please enter a number.")

    # The script now continues with the user's selected filename
    script_path = SELECTED_SCRIPTS_DIR / script_filename

    # Read the script content
    print(f"\nReading script: {script_path}...")
    try:
        text_content = script_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Failed to read script file: {e}")
        return

    # Split text into chunks
    print(f"Splitting text into chunks (limit: {CHUNK_LIMIT} characters)...")
    chunks = split_text(text_content, CHUNK_LIMIT)
    print(f"Split into {len(chunks)} chunks.")

    # Prepare output directory
    OUTPUT_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    # Determine output audio filename
    # Example: n8n_hosting_script_1.0.txt -> n8n_hosting_script_1.0.mp3
    output_audio_filename = script_path.stem + ".mp3"
    output_audio_path = OUTPUT_AUDIO_DIR / output_audio_filename

    combined_audio = AudioSegment.empty()

    print("\nStarting to Synthesize Audio Chunks...")

    for i, chunk in enumerate(chunks):
        temp_chunk_path = OUTPUT_AUDIO_DIR / f"temp_chunk_{i+1}.mp3"
        print(f"  Synthesizing chunk {i+1}/{len(chunks)}...")
        
        try:
            # Using with_streaming_response for potentially larger chunks and better handling
            with client.audio.speech.with_streaming_response.create(
                model="gpt-4o-mini-tts",  # Or "tts-1", "tts-1-hd"
                # voice="nova",             # Your preferred voice
                # model="tts-1", # Example alternative
                # voice="alloy", # Example alternative
                voice="echo",
                # voice="onyx",
                # voice="shimmer",
                # voice="fable",
                # voice="ash",
                instructions=TTS_INSTRUCTIONS, # Your detailed voice instructions
                input=chunk
            ) as response:
                response.stream_to_file(temp_chunk_path)
            
            combined_audio += AudioSegment.from_mp3(temp_chunk_path)
            os.remove(temp_chunk_path) # Clean up temporary chunk file

        except Exception as e:
            print(f"Error synthesizing chunk {i+1}: {e}")
            print("Skipping this chunk. Please check your API key, network, or content.")
            # Decide if you want to abort or continue with partial audio
            break # Abort the current synthesis on error

    if combined_audio: # Only export if audio was actually synthesized
        combined_audio.export(output_audio_path, format="mp3")
        print(f"\nSuccessfully synthesized and saved audio to: {output_audio_path}")
    else:
        print("\nAudio synthesis failed or produced no output.")

if __name__ == "__main__":
    synthesize_single_script()