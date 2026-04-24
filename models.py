"""
LLM Evaluation Pipeline - Model Query Module

Handles model querying, JSON schema enforcement, validation, and retry logic.
"""

import ollama
import time
import json
import re
from pydantic import create_model, ValidationError, Field
from typing import Annotated
from enum import Enum


# Default model settings - change these as needed
DEFAULT_TEMPERATURE = 0.1
DEFAULT_MAX_TOKENS = 150

# Placeholder detection constants
PLACEHOLDER_EXACT_VALUES = {
    "text", "string", "value", "example", "sample", "placeholder",
    "null", "none", "n/a", "na", "tbd", "tbc", "xxx", "abc", "word"
}

PLACEHOLDER_NUMBER_VALUES = {0, 0.0}  # Only 0 is placeholder, not 1.0


def load_schema(schema_file):
    """Load JSON schema from file and create Pydantic model."""
    with open(schema_file, "r") as f:
        schema_dict = json.load(f)
    
    model_name = schema_dict.get("name", "DynamicResponse")
    properties = schema_dict.get("properties", {})
    required_fields = schema_dict.get("required", [])
    
    field_definitions = {}
    
    for field_name, field_info in properties.items():
        field_type = field_info.get("type", "str")
        enum_values = field_info.get("enum", None)
        
        # Handle enum fields
        if enum_values:
            enum_class = Enum(f"{field_name}Enum", {v: v for v in enum_values})
            if field_name in required_fields:
                field_definitions[field_name] = (enum_class, ...)
            else:
                field_definitions[field_name] = (enum_class | None, None)
            continue
        
        # Handle numeric constraints
        if field_type in ("number", "integer"):
            ge = field_info.get("minimum")
            le = field_info.get("maximum")
            if field_type == "number":
                if ge is not None or le is not None:
                    anno = Annotated[float, Field(ge=ge, le=le)]
                    field_definitions[field_name] = (anno, ...)
                elif field_name in required_fields:
                    field_definitions[field_name] = (float, ...)
                else:
                    field_definitions[field_name] = (float | None, None)
            else:
                if ge is not None or le is not None:
                    anno = Annotated[int, Field(ge=ge, le=le)]
                    field_definitions[field_name] = (anno, ...)
                elif field_name in required_fields:
                    field_definitions[field_name] = (int, ...)
                else:
                    field_definitions[field_name] = (int | None, None)
            continue
        
        # Map other JSON types to Python types
        python_type = str
        if field_type == "boolean":
            python_type = bool
        elif field_type == "array":
            python_type = list
        elif field_type == "object":
            python_type = dict
        
        # Required fields are mandatory, optional fields default to None
        if field_name in required_fields:
            field_definitions[field_name] = (python_type, ...)
        else:
            field_definitions[field_name] = (python_type | None, None)
    
    DynamicModel = create_model(model_name, **field_definitions)
    
    return DynamicModel, schema_dict


def build_system_prompt(schema_dict):
    """Build system prompt that forces model to return JSON in the required format."""
    properties = schema_dict.get("properties", {})
    
    # Build example with valid enum values
    example_data = {}
    for field, info in properties.items():
        enum_vals = info.get("enum")
        if enum_vals:
            example_data[field] = enum_vals[0]  # Use first enum value
        elif info.get("type") == "number":
            example_data[field] = 0.5
        else:
            example_data[field] = "example"
    
    example_json = json.dumps(example_data)
    
    enum_info = ""
    for field, info in properties.items():
        if info.get("enum"):
            enum_info += f"{field}: {info['enum']}, "
    
    system_prompt = (
        f"You must respond with ONLY valid JSON. No text before or after. "
        f"Required fields: {enum_info[:-2]}. "
        f"Example: {example_json}"
    )
    return system_prompt


def build_retry_prompt(schema_dict):
    """Build retry prompt to handle failed validations."""
    properties = schema_dict.get("properties", {})
    
    example_data = {}
    for field, info in properties.items():
        enum_vals = info.get("enum")
        if enum_vals:
            example_data[field] = enum_vals[0]
        elif info.get("type") == "number":
            example_data[field] = 0.5
        else:
            example_data[field] = "example"
    
    return f"RETRY: Output ONLY valid JSON: {json.dumps(example_data)}"


def extract_json(text):
    """Extract JSON object from model response text."""
    text = text.strip()
    
    # Try direct parse first
    try:
        return json.loads(text)
    except:
        pass
    
    # Try extracting from markdown code blocks
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except:
            pass
    
    # Try finding first JSON object in text
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except:
            pass
    
    return None


def is_placeholder_value(value):
    """Check if a value looks like a placeholder (e.g., 'text', 0.5)."""
    if value is None:
        return True
    
    # Booleans are valid values
    if isinstance(value, bool):
        return False
    
    # Check for placeholder numbers
    if isinstance(value, (int, float)):
        return value in PLACEHOLDER_NUMBER_VALUES
    
    # Check for placeholder strings
    if isinstance(value, str):
        lower = value.lower().strip()
        
        if not lower:
            return True
        
        if lower in PLACEHOLDER_EXACT_VALUES:
            return True
        
        # Flag repeated characters like "aaa", "xxx"
        if len(lower) >= 3 and len(set(lower)) == 1:
            return True
    
    return False


def check_for_placeholders(data, schema_dict):
    """Check if response contains placeholder values."""
    required_fields = schema_dict.get("required", [])
    placeholders_found = []
    
    for field in required_fields:
        value = data.get(field)
        if is_placeholder_value(value):
            placeholders_found.append(field)
    
    if placeholders_found:
        return True, f"Placeholder values in: {', '.join(placeholders_found)}"
    
    return False, None


def parse_json_response(response_text, pydantic_model, schema_dict=None):
    """
    Parse and validate JSON response against Pydantic model.
    Returns: (validated_obj, validation_type, error_message)
    """
    try:
        extracted = extract_json(response_text)
        
        if extracted is None:
            return None, None, "Invalid JSON: no valid JSON found in response"
        
        # Validate against Pydantic model
        validated = pydantic_model.model_validate(extracted)
        return validated, None, None
        
    except json.JSONDecodeError as e:
        return None, None, f"JSON parse error: {str(e)}"
    except ValidationError as e:
        return None, None, f"Validation error: {str(e)}"
    except Exception as e:
        return None, None, f"Error: {str(e)}"


def query_model_stream(model, prompt, schema_file=None, max_retries=2):
    """
    Query Ollama model and optionally validate against JSON schema.
    
    Args:
        model: Model name to query
        prompt: User prompt
        schema_file: Path to JSON schema file (optional)
        max_retries: Number of retries on validation failure
    
    Returns:
        Dictionary with response, metrics, and validation results
    """
    pydantic_model = None
    schema_dict = None
    system_prompt = None
    
    # Load schema if provided
    if schema_file:
        pydantic_model, schema_dict = load_schema(schema_file)
        system_prompt = build_system_prompt(schema_dict)
    
# Build messages
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    # Query model - get full response for accurate metrics
    start_time = time.time()
    response = ollama.chat(
        model=model,
        messages=messages,
        stream=False,
        options={"num_predict": DEFAULT_MAX_TOKENS, "temperature": DEFAULT_TEMPERATURE}
    )
    end_time = time.time()
    
    # Extract accurate metrics from Ollama response
    full_response = response.get('message', {}).get('content', '')
    total_latency = response.get('total_duration', 0) / 1e9  # ns to seconds
    load_duration = response.get('load_duration', 0) / 1e9
    prompt_eval_duration = response.get('prompt_eval_duration', 0) / 1e9
    eval_duration = response.get('eval_duration', 0) / 1e9
    prompt_tokens = response.get('prompt_eval_count', 0)
    response_tokens = response.get('eval_count', 0)
    
    ttft = prompt_eval_duration  # Time to first token of response
    tps = response_tokens / eval_duration if eval_duration > 0 else None
    
    result = {
        "response": full_response,
        "total_latency": total_latency,
        "load_duration": load_duration,
        "ttft": ttft,
        "tps": tps,
        "tokens": response_tokens
    }
    
    # Validate response if schema provided
    if pydantic_model:
        validated_response, validation_type, error = parse_json_response(
full_response, pydantic_model, schema_dict
        )
        
        # Retry on validation failure
        retry_count = 0
        while (not validated_response or error is not None) and retry_count < max_retries:
            retry_count += 1
            print(f"  Retry {retry_count}/{max_retries}...")
            
            retry_prompt = build_retry_prompt(schema_dict)
            
            retry_response = ollama.chat(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": full_response[:200]},
                    {"role": "user", "content": retry_prompt}
                ],
                stream=False,
options={"num_predict": DEFAULT_MAX_TOKENS, "temperature": DEFAULT_TEMPERATURE}
            )
            
            full_response = retry_response.get('message', {}).get('content', '')
            
            validated_response, validation_type, error = parse_json_response(
                full_response, pydantic_model, schema_dict
            )
        
        # Set validation status
        if validated_response:
            result["validated_response"] = validated_response.model_dump()
            result["validation_status"] = "success"
        else:
            result["validated_response"] = None
            result["validation_status"] = "failed"
            result["validation_error"] = error
            result["raw_response"] = full_response
    
    return result