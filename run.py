import argparse
import subprocess
from evaluator import run
from utils import load_prompts


def get_available_models():
    result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
    return result.stdout


parser = argparse.ArgumentParser()

parser.add_argument("--models", nargs="+", required=True)
parser.add_argument("--file", type=str)
parser.add_argument("--prompt", type=str)

args = parser.parse_args()

# ✅ prompt handling
if args.prompt:
    prompts = [args.prompt]

elif args.file:
    prompts = load_prompts(args.file)

else:
    prompt = input("Enter your prompt: ")
    prompts = [prompt]


# ✅ model validation (important)
available_models = get_available_models()

valid_models = []
for model in args.models:
    if model in available_models:
        valid_models.append(model)
    else:
        print(f"[WARNING] Model '{model}' not found. Skipping.")

# ❌ if no valid models → stop
if not valid_models:
    raise ValueError("No valid models to run.")

# ✅ run benchmark
run(valid_models, prompts)