import os
import re
import time
from pathlib import Path
from moviepy.video.VideoClip import ImageClip
from moviepy.audio.io.AudioFileClip import AudioFileClip

from PIL import Image, ImageOps
from PIL.Image import Resampling
import numpy as np

# --- Configuration ---
# Project Name (Must match the one used in synthesize_batch.py)
PROJECT_NAME = "n8n-hosting-course"

# Define input and output directories relative to the project root
SELECTED_SCREENS_DIR = Path("_selected_screens")
AUDIO_INPUT_DIR = Path("1-audio_gen/output_audio") / PROJECT_NAME
CLIPS_OUTPUT_DIR = Path("2-video_clip_gen/output_clips")  

# Video output settings
VIDEO_SIZE = (1920, 1080) # W, H
FPS = 24 # Frames per second for output video clips

# --- Helper Function for Time Formatting ---
def format_seconds_to_min_sec(seconds: float) -> str:
    """
    Converts a duration in seconds into a human-readable "X min Y sec" format.
    """
    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)
    
    time_str = ""
    if minutes > 0:
        time_str += f"{minutes} min "
    time_str += f"{remaining_seconds} sec"
    return time_str

# --- FIX: Updated natural_sort_key for X.letter and X.letter.Y format ---
def natural_sort_key(s: str) -> list:
    """
    Key for natural sorting of IDs like '3.a', '3.c.0', '10.z'.
    Splits the string by '.' and converts parts to int if numeric, else keeps as string.
    This handles multiple levels of numeric/alphabetic sorting correctly.
    """
    parts = []
    for part in s.split('.'):
        if part.isdigit():
            parts.append(int(part))
        else:
            parts.append(part.lower()) # Ensure consistent case for letter comparison (e.g., 'A' vs 'a')
    return parts


# --- Main Single Clip Generation Function ---
def generate_single_clip():
    """
    Prompts the user to select an image/audio pair and generates a single video clip.
    """
    print("\n--- Stark Individual Video Clip Generator (Single File) ---")
    print(f"Project: {PROJECT_NAME}")

    # Ensure input directories exist
    if not SELECTED_SCREENS_DIR.exists():
        print(f"Error: Selected screens directory '{SELECTED_SCREENS_DIR}' not found.")
        print("Please ensure '_selected_screens' folder exists in the project root.")
        return

    if not AUDIO_INPUT_DIR.exists():
        print(f"Error: Audio input directory '{AUDIO_INPUT_DIR}' not found.")
        print("Please ensure you've run 'synthesize_batch.py' first and the project folder exists.")
        return

    # Create output directory for clips
    CLIPS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output clips will be saved to: {CLIPS_OUTPUT_DIR}")

    # --- 1. Collect and Map Files to find available pairs ---
    image_files = sorted([f for f in SELECTED_SCREENS_DIR.iterdir() if f.is_file() and f.suffix.lower() in ('.jpg', '.png')])
    audio_files = sorted([f for f in AUDIO_INPUT_DIR.iterdir() if f.is_file() and f.suffix.lower() == '.mp3'])

    # --- FIX: Updated regex patterns for X.letter and X.letter.Y format ---
    # Matches: img-3.a.jpg, img-3.c.0.jpg (captures '3.a' or '3.c.0')
    image_pattern = re.compile(r'img-(\d+\.[a-z](?:\.\d+)*)\.(?:jpg|png)', re.IGNORECASE)
    # Matches: n8n_hosting_script_3.a.mp3, n8n_hosting_script_3.c.0.mp3
    audio_pattern = re.compile(r'n8n_hosting_script_(\d+\.[a-z](?:\.\d+)*)\.mp3', re.IGNORECASE)

    matched_files = {}

    for img_path in image_files:
        match = image_pattern.search(img_path.name)
        if match:
            logical_id = match.group(1)
            if logical_id not in matched_files:
                matched_files[logical_id] = {'image': None, 'audio': None}
            matched_files[logical_id]['image'] = img_path
        else:
            print(f"  Warning: Could not extract logical ID from image: {img_path.name}. Skipping.")


    for audio_path in audio_files:
        match = audio_pattern.search(audio_path.name)
        if match:
            logical_id = match.group(1)
            if logical_id not in matched_files:
                matched_files[logical_id] = {'image': None, 'audio': None}
            matched_files[logical_id]['audio'] = audio_path
        else:
            print(f"  Warning: Could not extract logical ID from audio: {audio_path.name}. Skipping.")

    # Filter out unmatched files and sort by logical_id for consistent order
    available_pairs = []
    # Sort the logical_ids using the new natural_sort_key before iterating
    for logical_id in sorted(matched_files.keys(), key=natural_sort_key):
        pair = matched_files[logical_id]
        if pair['image'] and pair['audio']:
            available_pairs.append({'id': logical_id, 'image': pair['image'], 'audio': pair['audio']})
        else:
            if not pair['image']:
                print(f"  Warning: No image found for logical ID '{logical_id}'. Skipping pair.")
            if not pair['audio']:
                print(f"  Warning: No audio found for logical ID '{logical_id}'. Skipping pair.")


    if not available_pairs:
        print("No matching image-audio pairs found. Aborting clip generation.")
        return

    print(f"\nFound {len(available_pairs)} matching image-audio pairs to process.")
    for i, pair in enumerate(available_pairs):
        print(f"  {i+1}. Image: {pair['image'].name} | Audio: {pair['audio'].name}")

    # --- 2. User Selection ---
    selected_pair = None
    while selected_pair is None:
        user_input = input("\nPlease choose a number: ").strip()
        
        try:
            choice_index = int(user_input) - 1 # Convert to 0-based index
            if 0 <= choice_index < len(available_pairs):
                selected_pair = available_pairs[choice_index]
                print(f"Selected: {selected_pair['image'].name} & {selected_pair['audio'].name}")
            else:
                print(f"Error: Invalid number. Please enter a number between 1 and {len(available_pairs)}.")
        except ValueError:
            print("Error: Invalid input. Please enter a number.")

    # --- 3. Generate the Single Clip ---
    image_path = selected_pair['image']
    audio_path = selected_pair['audio']
    clip_start_time = time.time()

    print(f"\n--- Processing selected clip: {image_path.name} & {audio_path.name} ---")

    try:
        # 1. Load Audio and get duration
        audio_clip = AudioFileClip(str(audio_path))
        clip_duration = audio_clip.duration

        print(f"  Clip Duration (from audio): {format_seconds_to_min_sec(clip_duration)}")

        # 2. Load and process Image (resizing to VIDEO_SIZE)
        img = Image.open(image_path).convert("RGB")
        img = ImageOps.exif_transpose(img)
        img = img.resize(VIDEO_SIZE, Resampling.LANCZOS)
        img_array = np.array(img)
        
        # 3. Create ImageClip and attach audio
        video_clip = ImageClip(img_array, duration=clip_duration)
        final_video_clip = video_clip.with_audio(audio_clip)

        # 4. Define output filename for the clip
        # The output clip name should also reflect the new logical ID format
        output_clip_filename = f"{PROJECT_NAME}_clip_{selected_pair['id']}.mp4" 
        output_clip_path = CLIPS_OUTPUT_DIR / output_clip_filename

        # 5. Export the clip
        print(f"  Generating clip to: {output_clip_path}...")
        final_video_clip.write_videofile(
            str(output_clip_path),
            fps=FPS,
            codec='libx264',
            audio_codec='aac',
            logger=None
        )
        
        actual_time_taken = time.time() - clip_start_time
        print(f"Done! Clip generated successfully. Time Taken: {format_seconds_to_min_sec(actual_time_taken)}")
        print("\n----------------------------------------------------------")
        print("Single Video Clip Generation Complete!")
        print(f"Output Clip Location: {output_clip_path}")
        print(f"Clip Duration: {format_seconds_to_min_sec(final_video_clip.duration)}")
        print("----------------------------------------------------------")

    except Exception as e:
        print(f"Error generating clip for {image_path.name} & {audio_path.name}: {e}")
        print("Aborting single clip generation due to error.")
    finally:
        if 'audio_clip' in locals() and audio_clip:
            audio_clip.close()
        if 'video_clip' in locals() and video_clip:
            video_clip.close()
        if 'final_video_clip' in locals() and final_video_clip:
            final_video_clip.close()


if __name__ == "__main__":
    generate_single_clip()