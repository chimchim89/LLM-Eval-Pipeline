"""
LLM Evaluation Pipeline - CLI Entry Point

Run benchmarks on Ollama models with optional JSON schema validation.
"""

import argparse
import subprocess
from evaluator import run
from utils import load_prompts


def get_available_models():
    """Get list of available Ollama models."""
    result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
    return result.stdout


# Parse command line arguments
parser = argparse.ArgumentParser(description="LLM Evaluation Pipeline")

parser.add_argument("--models", nargs="+", required=True, help="Models to evaluate")
parser.add_argument("--fallback-models", nargs="*", default=[], 
                    help="Fallback models if primary fails validation")
parser.add_argument("--file", type=str, help="File containing prompts (one per line)")
parser.add_argument("--prompt", type=str, help="Single prompt to evaluate")
parser.add_argument("--schema", type=str, help="JSON schema file for output validation")

args = parser.parse_args()

# Load prompts from file or command line
if args.prompt:
    prompts = [args.prompt]
elif args.file:
    prompts = load_prompts(args.file)
else:
    prompts = [input("Enter your prompt: ")]

# Get available models and filter to only valid ones
available_models = get_available_models()

valid_models = []
for model in args.models:
    if model in available_models:
        valid_models.append(model)
    else:
        print(f"[WARNING] Model '{model}' not found. Skipping.")

valid_fallback_models = []
for model in args.fallback_models:
    if model in available_models:
        valid_fallback_models.append(model)
    else:
        print(f"[WARNING] Fallback model '{model}' not found. Skipping.")

# Ensure at least one valid model
if not valid_models:
    raise ValueError("No valid models to run.")

# Run benchmark
run(
    models=valid_models,
    prompts=prompts,
    schema_file=args.schema,
    fallback_models=valid_fallback_models
)