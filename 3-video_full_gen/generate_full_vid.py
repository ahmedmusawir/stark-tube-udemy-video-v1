from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy import concatenate_videoclips
from moviepy import vfx

from pathlib import Path
import re
import time
import os
import sys
from contextlib import contextmanager
import warnings # <--- To skip harmless warnings

# THIS LINE HIDES THE HARMLESS FFMPEG WARNING
warnings.filterwarnings("ignore", message=".*bytes wanted but 0 bytes read.*") 

@contextmanager
def suppress_stdout_stderr():
    with open(os.devnull, 'w') as fnull:
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = fnull, fnull
        try:
            yield
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr

# --- Configuration ---
PROJECT_NAME = "n8n-hosting-course" 
CLIPS_INPUT_DIR = Path("2-video_clip_gen/output_clips") / PROJECT_NAME
FINAL_OUTPUT_DIR = Path("3-video_full_gen/output_final") / PROJECT_NAME
FINAL_VIDEO_FILENAME = f"{PROJECT_NAME}_full_video.mp4"
TRANSITION_DURATION = 0.75 
FPS = 24

# --- Helper Functions (unchanged) ---
def format_seconds_to_min_sec(seconds: float) -> str:
    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)
    time_str = ""
    if minutes > 0:
        time_str += f"{minutes} min "
    time_str += f"{remaining_seconds} sec"
    return time_str

def natural_sort_key(s: str) -> list:
    return [float(c) if c.replace('.', '').isdigit() else c for c in re.split(r'(\d+(?:\d+)*)', s)]

# --- Main Full Video Generation Function ---
def generate_full_video():
    print("\n--- Stark Full Video Generator ---")
    print(f"Project: {PROJECT_NAME}")

    # ... (File checking code is the same) ...
    if not CLIPS_INPUT_DIR.exists():
        print(f"Error: Input clips directory '{CLIPS_INPUT_DIR}' not found.")
        return

    clip_files = sorted([f for f in CLIPS_INPUT_DIR.iterdir() if f.is_file() and f.suffix.lower() == '.mp4'], 
                        key=lambda p: natural_sort_key(p.name))

    if not clip_files:
        print(f"No video clips found in '{CLIPS_INPUT_DIR}'.")
        return

    print(f"\nFound {len(clip_files)} clips to stitch together:")
    total_duration_raw_clips = 0.0
    valid_clip_files = []

    for i, clip_path in enumerate(clip_files):
        try:
            with suppress_stdout_stderr():
                with VideoFileClip(str(clip_path)) as temp_clip: 
                    clip_duration = temp_clip.duration
            
            total_duration_raw_clips += clip_duration
            print(f"  {i+1}. {clip_path.name} ({format_seconds_to_min_sec(clip_duration)})")
            valid_clip_files.append(clip_path)
        except Exception as e:
            print(f"  Warning: Could not read or process clip {clip_path.name} ({e}). Skipping.")
    
    if not valid_clip_files:
        print("No valid clips could be loaded. Aborting.")
        return

    print(f"\nEstimated total duration of raw clips: {format_seconds_to_min_sec(total_duration_raw_clips)}")

    proceed = input("\nDoes the list of clips look good to proceed? (y/n): ").lower().strip()
    if proceed != 'y':
        print("Aborted by user.")
        return

    loaded_moviepy_clips = []
    final_video = None
    try:
        print("\nLoading clips and preparing transitions...")
        num_clips = len(valid_clip_files)

        for i, clip_path in enumerate(valid_clip_files):
            with suppress_stdout_stderr():
                clip = VideoFileClip(str(clip_path))

            # Define the effects for this specific clip
            effects_to_apply = []
            if i > 0:
                effects_to_apply.append(vfx.FadeIn(TRANSITION_DURATION))
            if i < num_clips - 1:
                effects_to_apply.append(vfx.FadeOut(TRANSITION_DURATION))
            
            if effects_to_apply:
                clip = clip.with_effects(effects_to_apply)
            
            loaded_moviepy_clips.append(clip)

        if not loaded_moviepy_clips:
            print("No clips were successfully loaded for concatenation. Aborting.")
            return

        print(f"\nStitching {len(loaded_moviepy_clips)} clips...")
        start_time = time.time()
        
        final_video = concatenate_videoclips(loaded_moviepy_clips, method="compose")

        FINAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_filepath = FINAL_OUTPUT_DIR / FINAL_VIDEO_FILENAME

        print(f"Exporting final video to: {output_filepath}...")
        final_video.write_videofile(
            str(output_filepath), 
            fps=FPS, 
            codec='libx264',
            audio_codec='aac',
            preset='faster',
            threads=8,
            logger=None
        )
        
        end_time = time.time()
        time_taken = end_time - start_time

        print("\n----------------------------------------------------------")
        print("Full Video Generation Complete!")
        print(f"Output Video Location: {output_filepath}")
        print(f"Time Taken: {format_seconds_to_min_sec(time_taken)}")
        print(f"Final Video Duration: {format_seconds_to_min_sec(final_video.duration)}")
        print("----------------------------------------------------------")

    except Exception as e:
        print(f"\nAn unexpected error occurred during video stitching or export: {e}")
    finally:
        if final_video:
            final_video.close()
        for clip in loaded_moviepy_clips:
            clip.close()

if __name__ == "__main__":
    generate_full_video()