# LLM Evaluation Pipeline

Benchmarks local Ollama models with structured JSON output validation.

## Features

- **Performance Metrics**
  - Tokens per second (TPS)
  - Time to first token (TTFT)
  - Total response latency

- **Output Validation**
  - JSON schema enforcement
  - Pydantic validation (enum, types, range constraints)
  - Retry mechanism on invalid outputs
  - Graceful failure handling

## Prerequisites

1. Install [Ollama](https://ollama.com/)
2. Pull a model: `ollama pull llama3.2:3b`
3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Basic benchmark
python run.py --models llama3.2:3b --prompt "Your prompt"

# With schema validation
python run.py --models llama3.2:3b --prompt "I love this product" --schema schema.json
```

### Command Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `--models` | Model name to evaluate | Yes |
| `--prompt` | Prompt to test | Yes |
| `--schema` | JSON schema file for validation | No |
| `--file` | File with prompts (one per line) | No |
| `--fallback-models` | Fallback if primary fails | No |

## Configuration

Edit defaults in `models.py`:

```python
DEFAULT_TEMPERATURE = 0.1
DEFAULT_MAX_TOKENS = 150
```

## Benchmark Results

| Model | Size | TTFT | TPS | Latency | Valid JSON |
|-------|------|------|-----|---------|------------|
| llama3.2:3b | 2.0 GB | ~15s | ~4 | ~30s | ✓ |
| tinyllama | 637 MB | - | - | - | - |
| qwen2.5:0.5b | 397 MB | - | - | - | - |

## Output Example

```
=== llama3.2:3b ===
Schema Validation: PASSED

Prompt: I love this product
TTFT: 14.84s
Total Latency: 29.56s
TPS: 4.15 tokens/sec
Tokens: 26
Response: {"sentiment": "positive", "confidence": 0.9, "reasoning": "Liking the product"}
```

## Project Structure

```
LLM-Eval-Pipeline/
├── run.py           # CLI entry point
├── models.py        # Model querying & validation
├── evaluator.py    # Benchmark runner
├── schema.py       # Pydantic models
├── schema.json    # JSON output schema
├── utils.py       # Utilities
└── results/       # Benchmark results
```

## Demo

[Loom Video Link]

## License

MIT