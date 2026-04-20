import ollama
import time


def query_model_stream(model, prompt):
    start_time = time.time()
    first_token_time = None

    full_response = ""
    token_count = 0

    stream = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        stream=True,
        options={"num_predict": 100}
    )

    for chunk in stream:
        if 'message' in chunk and 'content' in chunk['message']:
            token = chunk['message']['content']

            if first_token_time is None:
                first_token_time = time.time()

            full_response += token
            token_count += 1

    end_time = time.time()

    total_latency = end_time - start_time
    ttft = first_token_time - start_time if first_token_time else None
    generation_time = end_time - first_token_time if first_token_time else 0

    tps = token_count / generation_time if generation_time > 0 else None

    return {
        "response": full_response,
        "total_latency": total_latency,
        "ttft": ttft,
        "tps": tps,
        "tokens": token_count
    }
