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
PROJECT_NAME = "coach-dashboard"
SELECTED_SCREENS_DIR = Path("_selected_screens")
AUDIO_INPUT_DIR = Path("1-audio_gen/output_audio") / PROJECT_NAME
CLIPS_OUTPUT_DIR = Path("2-video_clip_gen/output_clips") / PROJECT_NAME
VIDEO_SIZE = (1920, 1080)
FPS = 24

# --- Helper Function for Time Formatting ---
def format_seconds_to_min_sec(seconds: float) -> str:
    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)
    time_str = ""
    if minutes > 0:
        time_str += f"{minutes} min "
    time_str += f"{remaining_seconds} sec"
    return time_str

### --- SECTION 1: UPDATED SORTING LOGIC --- ###
def natural_sort_key(file_path: Path) -> int:
    """
    Key for natural sorting of filenames ending in numbers (e.g., 'coach-dash-0005').
    Extracts the trailing number from the filename stem for proper numeric sorting.
    """
    match = re.search(r'(\d+)$', file_path.stem)
    if match:
        return int(match.group(1))
    # Fallback for any files that might not end in a number
    return 0

# --- Main Clip Generation Function ---
def generate_individual_clips():
    """
    Matches images with audio files based on shared filenames, generates individual video clips,
    and reports on progress and total duration.
    """
    print("\n--- Stark Individual Video Clip Generator ---")
    print(f"Project: {PROJECT_NAME}")

    if not SELECTED_SCREENS_DIR.exists():
        print(f"Error: Selected screens directory '{SELECTED_SCREENS_DIR}' not found.")
        return
    
    # if not AUDIO_INPUT_DIR.exists():
    #     print(f"Error: Audio input directory '{AUDIO_INPUT_DIR}' not found.")
    #     return

    if not AUDIO_INPUT_DIR.exists():
        print(f"Heads up: The audio input directory '{AUDIO_INPUT_DIR}' was not found.")
        create_it = input("Shall I create this directory for you? (y/n): ").lower().strip()
        if create_it == 'y':
            AUDIO_INPUT_DIR.mkdir(parents=True, exist_ok=True)
            print(f"Directory created. Please add your '{PROJECT_NAME}' MP3 files to it and run this script again.")
        else:
            print("Understood. Aborting script.")
        return # Stop the script either way, as the new folder will be empty.

    CLIPS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output clips will be saved to: {CLIPS_OUTPUT_DIR}")

    ### --- SECTION 2: SIMPLIFIED FILE MATCHING LOGIC --- ###
    print("\nMatching images to audio files based on filename...")

    # 1. Collect and sort all image and audio files using the new key
    image_files = sorted(
        [f for f in SELECTED_SCREENS_DIR.iterdir() if f.is_file() and f.suffix.lower() in ('.jpg', '.png')],
        key=natural_sort_key
    )
    audio_files = sorted(
        [f for f in AUDIO_INPUT_DIR.iterdir() if f.is_file() and f.suffix.lower() == '.mp3'],
        key=natural_sort_key
    )

    # 2. Create a dictionary mapping the filename stem to the full path for quick lookups
    image_map = {p.stem: p for p in image_files}
    audio_map = {p.stem: p for p in audio_files}

    # 3. Find the common stems (logical IDs) that exist in both directories
    common_stems = sorted(
        list(set(image_map.keys()) & set(audio_map.keys())),
        key=lambda s: int(re.search(r'(\d+)$', s).group(1)) # Sort the final list numerically
    )

    # 4. Build the final list of paired items
    paired_items = []
    for stem in common_stems:
        paired_items.append({
            'image': image_map[stem],
            'audio': audio_map[stem],
            'id': stem  # Store the stem as our logical ID
        })
    
    if not paired_items:
        print("No matching image-audio pairs found based on filenames. Aborting clip generation.")
        # Provide guidance if no pairs are found
        print("\nPlease ensure that for every 'name-0001.jpg' in '_selected_screens', there is a corresponding 'name-0001.mp3' in the audio output directory.")
        return

    print(f"\nFound {len(paired_items)} matching image-audio pairs to process:")
    for i, item in enumerate(paired_items):
        print(f"  {i+1}. Image: {item['image'].name} | Audio: {item['audio'].name}")

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
        logical_id = item['id'] # Use the stored ID
        clip_start_time = time.time()

        print(f"\n--- Processing Clip {i+1}/{len(paired_items)}: {image_path.name} & {audio_path.name} ---")

        try:
            audio_clip = AudioFileClip(str(audio_path))
            clip_duration = audio_clip.duration
            total_combined_clip_duration_sec += clip_duration

            print(f"  Clip Duration (from audio): {format_seconds_to_min_sec(clip_duration)}")

            img = Image.open(image_path).convert("RGB")
            img = ImageOps.exif_transpose(img)
            img = img.resize(VIDEO_SIZE, Resampling.LANCZOS)
            img_array = np.array(img)
            
            video_clip = ImageClip(img_array, duration=clip_duration)
            final_video_clip = video_clip.with_audio(audio_clip)

            ### --- SECTION 3: UPDATED OUTPUT FILENAME LOGIC --- ###
            # Use the simple logical_id (stem) for the output filename
            output_clip_filename = f"{PROJECT_NAME}_clip_{logical_id}.mp4"
            output_clip_path = CLIPS_OUTPUT_DIR / output_clip_filename

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
        finally:
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