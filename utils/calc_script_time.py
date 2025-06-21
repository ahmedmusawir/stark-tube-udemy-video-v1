import os

# Define the path to your _selected_scripts folder relative to the project root
# Assuming utils/calc_script_time.py is run from the project root
SCRIPTS_DIR = '_selected_scripts'

# Average speaking rate: 150 words per minute, which is 2.5 words per second
WORDS_PER_SECOND = 2.5

def calculate_script_times():
    """
    Calculates estimated audio length for each script file and a total.
    """
    if not os.path.exists(SCRIPTS_DIR):
        print(f"Error: Script directory '{SCRIPTS_DIR}' not found. Please ensure the path is correct.")
        return

    script_files = sorted([f for f in os.listdir(SCRIPTS_DIR) if f.endswith('.txt')])

    if not script_files:
        print(f"No .txt script files found in '{SCRIPTS_DIR}'.")
        return

    total_words = 0
    report_lines = []

    print(f"\n--- Estimating Audio Lengths for Scripts in '{SCRIPTS_DIR}' ---")

    for filename in script_files:
        filepath = os.path.join(SCRIPTS_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                words = len(content.split())
                
                estimated_seconds = words / WORDS_PER_SECOND
                
                minutes = int(estimated_seconds // 60)
                seconds = int(estimated_seconds % 60)

                total_words += words

                time_str = ""
                if minutes > 0:
                    time_str += f"{minutes} min "
                time_str += f"{seconds} sec"

                report_lines.append(f"{filename} --> {words} words --> {time_str}")

        except Exception as e:
            report_lines.append(f"Error processing {filename}: {e}")

    print("\n".join(report_lines))
    print("----------------------------------------------------------")
    
    total_estimated_seconds = total_words / WORDS_PER_SECOND
    total_minutes = int(total_estimated_seconds // 60)
    total_seconds = int(total_estimated_seconds % 60)

    total_time_str = ""
    if total_minutes > 0:
        total_time_str += f"{total_minutes} min "
    total_time_str += f"{total_seconds} sec"

    print(f"Total --> {total_words} words --> {total_time_str}")
    print("----------------------------------------------------------")

if __name__ == "__main__":
    calculate_script_times()