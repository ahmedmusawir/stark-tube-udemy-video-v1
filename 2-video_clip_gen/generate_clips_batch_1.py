import os
import re
import time
from pathlib import Path
# Corrected imports for MoviePy 2.x based on specific module paths:
from moviepy.video.VideoClip import ImageClip # Correct for ImageClip in MoviePy 2.x
from moviepy.audio.io.AudioFileClip import AudioFileClip # Correct for AudioFileClip in MoviePy 2.x
# If concatenate_videoclips is needed for batching later, it's typically:
# from moviepy.video.compositing.concatenate import concatenate_videoclips 

from PIL import Image, ImageOps 
from PIL.Image import Resampling 
import numpy as np 

# --- Configuration ---
# Project Name (Must match the one used in synthesize_batch.py)
PROJECT_NAME = "n8n-hosting-course" 

# Define input and output directories relative to the project root
# The script expects to be run from the project root directory
SELECTED_SCREENS_DIR = Path("_selected_screens")
AUDIO_INPUT_DIR = Path("1-audio_gen/output_audio") / PROJECT_NAME
CLIPS_OUTPUT_DIR = Path("2-video_clip_gen/output_clips") / PROJECT_NAME # NO CHANGE HERE, THIS IS CORRECT

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

# --- START OF REQUIRED CHANGES ---

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

# --- Main Clip Generation Function ---
def generate_individual_clips():
    """
    Matches images with audio files, generates individual video clips,
    and reports on progress and total duration.
    """
    print("\n--- Stark Individual Video Clip Generator ---")
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

    # --- 1. Collect and Map Files ---
    image_files = sorted([f for f in SELECTED_SCREENS_DIR.iterdir() if f.is_file() and f.suffix.lower() in ('.jpg', '.png')])
    audio_files = sorted([f for f in AUDIO_INPUT_DIR.iterdir() if f.is_file() and f.suffix.lower() == '.mp3'])

    # --- FIX: Updated regex patterns for X.letter and X.letter.Y format ---
    # Matches: img-3.a.jpg, img-3.c.0.jpg (captures '3.a' or '3.c.0')
    image_pattern = re.compile(r'img-(\d+\.[a-z](?:\.\d+)*)\.(?:jpg|png)', re.IGNORECASE) 
    # Matches: n8n_hosting_script_3.a.mp3, n8n_hosting_script_3.c.0.mp3
    audio_pattern = re.compile(r'n8n_hosting_script_(\d+\.[a-z](?:\.\d+)*)\.mp3', re.IGNORECASE) 

    matched_files = {} 

    print("\nMatching images to audio files...")
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
    # The natural_sort_key function is now defined above this block.
    paired_items = []
    # Sort the logical_ids using the new natural_sort_key before iterating
    for logical_id in sorted(matched_files.keys(), key=natural_sort_key):
        pair = matched_files[logical_id]
        if pair['image'] and pair['audio']:
            paired_items.append(pair)
        else:
            if not pair['image']:
                print(f"  Warning: No image found for logical ID '{logical_id}'. Skipping pair.")
            if not pair['audio']:
                print(f"  Warning: No audio found for logical ID '{logical_id}'. Skipping pair.")

    if not paired_items:
        print("No matching image-audio pairs found. Aborting clip generation.")
        return

    print(f"\nFound {len(paired_items)} matching image-audio pairs to process.")
    for i, item in enumerate(paired_items):
        print(f"  {i+1}. Image: {item['image'].name} | Audio: {item['audio'].name}")

    # User verification before proceeding
    proceed = input("\nDoes the list of pairs look good to proceed? (y/n): ").lower().strip()
    if proceed != 'y':
        print("Clip generation aborted by user.")
        return

    total_clips_generated = 0
    total_combined_clip_duration_sec = 0.0
    
    print("\nStarting Individual Clip Generation...")

    for i, item in enumerate(paired_items):
        image_path = item['image']
        audio_path = item['audio']
        clip_start_time = time.time()

        print(f"\n--- Processing Clip {i+1}/{len(paired_items)}: {image_path.name} & {audio_path.name} ---")

        try:
            # 1. Load Audio and get duration
            audio_clip = AudioFileClip(str(audio_path))
            clip_duration = audio_clip.duration
            total_combined_clip_duration_sec += clip_duration

            print(f"  Clip Duration (from audio): {format_seconds_to_min_sec(clip_duration)}")

            # 2. Load and process Image (resizing to VIDEO_SIZE)
            img = Image.open(image_path).convert("RGB")
            img = ImageOps.exif_transpose(img) 
            img = img.resize(VIDEO_SIZE, Resampling.LANCZOS) 
            img_array = np.array(img)
            
            # 3. Create ImageClip and attach audio
            video_clip = ImageClip(img_array, duration=clip_duration)
            # CORRECTED: Use .with_audio() method in MoviePy 2.x
            final_video_clip = video_clip.with_audio(audio_clip)

            # 4. Define output filename for the clip
            # The output clip name should also reflect the new logical ID format
            logical_id = image_pattern.search(image_path.name).group(1) # This will now extract X.letter or X.letter.Y
            output_clip_filename = f"{PROJECT_NAME}_clip_{logical_id}.mp4"
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
            total_clips_generated += 1

        except Exception as e:
            print(f"Error generating clip for {image_path.name} & {audio_path.name}: {e}")
            print("Skipping this pair...")
        finally: # Added for robust resource closing
            if 'audio_clip' in locals() and audio_clip:
                audio_clip.close()
            if 'video_clip' in locals() and video_clip:
                video_clip.close()
            if 'final_video_clip' in locals() and final_video_clip:
                final_video_clip.close()


    print("\n----------------------------------------------------------")
    print("Individual Video Clip Generation Complete!")
    print(f"Total clips generated: {total_clips_generated}")
    print(f"Total combined length of all clips: {format_seconds_to_min_sec(total_combined_clip_duration_sec)}")
    print("----------------------------------------------------------")

if __name__ == "__main__":
    generate_individual_clips()