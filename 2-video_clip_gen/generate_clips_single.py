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
SELECTED_SCREENS_DIR = Path("selected_screens")
AUDIO_INPUT_DIR = Path("1-audio_gen/output_audio") / PROJECT_NAME
# As requested, this output path is kept as is.
CLIPS_OUTPUT_DIR = Path("2-video_clip_gen/output_clips")

# Video output settings
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
    return 0


# --- Main Single Clip Generation Function ---
def generate_single_clip():
    """
    Prompts the user to select an image/audio pair and generates a single video clip.
    """
    print("\n--- Stark Individual Video Clip Generator (Single File) ---")
    print(f"Project: {PROJECT_NAME}")

    if not SELECTED_SCREENS_DIR.exists():
        print(f"Error: Selected screens directory '{SELECTED_SCREENS_DIR}' not found.")
        return
    if not AUDIO_INPUT_DIR.exists():
        print(f"Error: Audio input directory '{AUDIO_INPUT_DIR}' not found.")
        return

    CLIPS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output clips will be saved to: {CLIPS_OUTPUT_DIR}")

    ### --- SECTION 2: SIMPLIFIED FILE MATCHING LOGIC --- ###
    # 1. Collect and sort files using the new key
    image_files = sorted(
        [f for f in SELECTED_SCREENS_DIR.iterdir() if f.is_file() and f.suffix.lower() in ('.jpg', '.png')],
        key=natural_sort_key
    )
    audio_files = sorted(
        [f for f in AUDIO_INPUT_DIR.iterdir() if f.is_file() and f.suffix.lower() == '.mp3'],
        key=natural_sort_key
    )

    # 2. Map filename stems to full paths
    image_map = {p.stem: p for p in image_files}
    audio_map = {p.stem: p for p in audio_files}

    # 3. Find common stems (logical IDs)
    common_stems = sorted(
        list(set(image_map.keys()) & set(audio_map.keys())),
        key=lambda s: int(re.search(r'(\d+)$', s).group(1))
    )

    # 4. Build the list of available pairs for the user to choose from
    available_pairs = []
    for stem in common_stems:
        available_pairs.append({
            'image': image_map[stem],
            'audio': audio_map[stem],
            'id': stem
        })

    if not available_pairs:
        print("No matching image-audio pairs found. Aborting clip generation.")
        print("\nPlease ensure that for every 'name-0001.jpg' in '_selected_screens', there is a corresponding 'name-0001.mp3' in the audio output directory.")
        return

    # This part of the logic for user interaction is preserved
    print(f"\nFound {len(available_pairs)} matching image-audio pairs to process.")
    for i, pair in enumerate(available_pairs):
        print(f"  {i+1}. Image: {pair['image'].name} | Audio: {pair['audio'].name}")

    # --- 2. User Selection ---
    selected_pair = None
    while selected_pair is None:
        user_input = input("\nPlease choose a number: ").strip()
        try:
            choice_index = int(user_input) - 1
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
    logical_id = selected_pair['id'] # Use the clean ID
    clip_start_time = time.time()

    print(f"\n--- Processing selected clip: {image_path.name} & {audio_path.name} ---")

    try:
        audio_clip = AudioFileClip(str(audio_path))
        clip_duration = audio_clip.duration
        print(f"  Clip Duration (from audio): {format_seconds_to_min_sec(clip_duration)}")

        img = Image.open(image_path).convert("RGB")
        img = ImageOps.exif_transpose(img)
        img = img.resize(VIDEO_SIZE, Resampling.LANCZOS)
        img_array = np.array(img)
        
        video_clip = ImageClip(img_array, duration=clip_duration)
        final_video_clip = video_clip.with_audio(audio_clip)

        # The output filename uses the new, clean logical ID
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