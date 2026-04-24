"""
LLM Evaluation Pipeline - Evaluator Module

Runs benchmark evaluations on multiple models with fallback support.
"""

from schema import BenchmarkResult
from models import query_model_stream
import os
import uuid


def run(models, prompts, schema_file=None, fallback_models=None):
    """
    Run evaluation on multiple models.
    
    Args:
        models: List of model names to evaluate
        prompts: List of prompts to test
        schema_file: Path to JSON schema for validation (optional)
        fallback_models: List of fallback models if primary fails (optional)
    
    Returns:
        List of benchmark results
    """
    if fallback_models is None:
        fallback_models = []
    
    results = []
    
    # Create results directory if it doesn't exist
    os.makedirs("results", exist_ok=True)
    
    # Evaluate each model
    for model in models:
        print(f"\n=== {model} ===")
        
        for prompt in prompts:
            request_id = str(uuid.uuid4())
            result = None
            error = None
            used_fallback = False
            
            # Try primary model first
            try:
                result = query_model_stream(model, prompt, schema_file=schema_file)
                
                # If validation failed and fallback models available, try them
                if (schema_file and 
                    result.get("validation_status") == "failed" and 
                    fallback_models):
                    
                    print(f"  Primary model failed, trying fallbacks...")
                    
                    for fallback_model in fallback_models:
                        print(f"  Trying fallback: {fallback_model}")
                        try:
                            result = query_model_stream(
                                fallback_model, prompt, schema_file=schema_file
                            )
                            if result.get("validation_status") == "success":
                                print(f"  Fallback {fallback_model} succeeded!")
                                used_fallback = True
                                break
                        except Exception as e:
                            print(f"  Fallback {fallback_model} error: {e}")
                            continue
                            
            except Exception as e:
                error = str(e)
            
            # Create benchmark result record
            if result is not None and result.get("tokens", 0) > 0:
                benchmark_result = BenchmarkResult(
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
                
                # Print validation results if schema provided
                if schema_file:
                    validation_status = result.get("validation_status", "none")
                    if validation_status == "success":
                        status_str = "PASSED"
                        if used_fallback:
                            status_str = "PASSED (via fallback)"
                        print(f"Schema Validation: {status_str}")
                        print(f"Validated Response: {result.get('validated_response')}")
                    else:
                        print(f"Schema Validation: FAILED")
                        print(f"Validation Error: {result.get('validation_error')}")
                        print(f"Raw Response: {result.get('raw_response', '')[:200]}...")
            else:
                benchmark_result = BenchmarkResult(
                    request_id=request_id,
                    model=model,
                    prompt=prompt,
                    status="failed",
                    level="ERROR",
                    event="error",
                    error=error or "Model failed or returned no output"
                )
            
            # Print results
            if benchmark_result.status == "failed":
                print(f"[{model}] FAILED -> {benchmark_result.error}")
            else:
                print(f"\nPrompt: {benchmark_result.prompt}")
                print(f"TTFT: {benchmark_result.ttft:.2f}s")
                print(f"Total Latency: {benchmark_result.total_latency:.2f}s")
                print(f"TPS: {benchmark_result.tps:.2f} tokens/sec")
                print(f"Tokens: {benchmark_result.tokens}")
                print(f"Response: {benchmark_result.response[:100]}...")
            
            # Store and save result
            results.append(benchmark_result.model_dump())
            
            with open("results/results.json", "a") as f:
                f.write(benchmark_result.model_dump_json() + "\n")
    
    return results