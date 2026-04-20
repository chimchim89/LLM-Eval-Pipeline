from schema import BenchmarkResult
from models import query_model_stream
import os
import uuid


def run(models, prompts):
    results = []

    # ensure results folder exists
    os.makedirs("results", exist_ok=True)

    for model in models:
        print(f"\n=== {model} ===")

        for prompt in prompts:

            request_id = str(uuid.uuid4())  # ✅ unique per request

            result = None
            error = None

            try:
                result = query_model_stream(model, prompt)
                status = "success"

            except Exception as e:
                status = "failed"
                error = str(e)

            # ✅ create validated object
            if result is not None and result.get("tokens", 0) > 0:
                validated = BenchmarkResult(
                    request_id=request_id,
                    model=model,
                    prompt=prompt,
                    status="success",
                    level="INFO",
                    event="response_received",
                    response=result['response'],
                    ttft=result['ttft'],
                    total_latency=result['total_latency'],
                    tps=result['tps'],
                    tokens=result['tokens']
                )
            else:
                validated = BenchmarkResult(
                    request_id=request_id,
                    model=model,
                    prompt=prompt,
                    status="failed",
                    level="ERROR",
                    event="error",
                    error=error or "Model failed or returned no output"
                )

            # ✅ clean terminal output
            if validated.status == "failed":
                print(f"\n[{model}] ❌ FAILED → {validated.error}")

            else:
                print(f"\nPrompt: {validated.prompt}")
                print(f"TTFT: {validated.ttft:.2f}s")
                print(f"Total Latency: {validated.total_latency:.2f}s")
                print(f"TPS: {validated.tps:.2f} tokens/sec")
                print(f"Tokens: {validated.tokens}")
                print(f"Response: {validated.response[:100]}...")

            # ✅ store structured result
            results.append(validated.model_dump())

            # ✅ save to JSONL
            with open("results/results.json", "a") as f:
                f.write(validated.model_dump_json() + "\n")

    return results