"""
LLM Evaluation Pipeline - Utility Functions
"""

def load_prompts(path):
    """Load prompts from file (one prompt per line)."""
    with open(path, "r") as f:
        return [line.strip() for line in f if line.strip()]