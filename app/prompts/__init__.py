import os

PROMPTS_DIR = os.path.dirname(os.path.abspath(__file__))

def load_prompt_template(name):
    """Loads a prompt template from text file by name."""
    file_path = os.path.join(PROMPTS_DIR, f"{name}.txt")
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""
    return ""

def get_all_prompts():
    """Returns a dictionary containing all prompt templates."""
    prompts = {}
    for filename in os.listdir(PROMPTS_DIR):
        if filename.endswith(".txt"):
            name = filename[:-4]
            prompts[name] = load_prompt_template(name)
    return prompts
