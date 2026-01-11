# src/utils.py

import os
import logging
import requests

def call_responses_api(
    model,
    prompt,
    openai_api_key,
    instructions="",
    max_output_tokens=500,
    temperature=1.0
):
    """
    Calls OpenAI's 'Responses API' (POST /v1/responses) with a single text prompt.
    Returns the text output from the first item in the 'output' array.
    Raises an exception if errors occur.
    """
    url = "https://api.openai.com/v1/responses"
    headers = {
        "Authorization": f"Bearer {openai_api_key}",
        "Content-Type": "application/json",
    }
    # gpt-5 models use reasoning tokens that count against max_output_tokens
    # Need higher limit to leave room for actual output after reasoning
    effective_max_tokens = max_output_tokens
    if model.startswith("gpt-5"):
        effective_max_tokens = max(max_output_tokens * 4, 4096)

    data = {
        "model": model,
        "input": prompt,
        "max_output_tokens": effective_max_tokens
    }
    # gpt-5 models: no temperature, use low reasoning effort for speed
    if model.startswith("gpt-5"):
        data["reasoning"] = {"effort": "low"}
    else:
        data["temperature"] = temperature
    if instructions:
        data["instructions"] = instructions

    resp = requests.post(url, headers=headers, json=data)
    if not resp.ok:
        logging.error(f"OpenAI Responses API error. Status: {resp.status_code}, Body: {resp.text}")
        resp.raise_for_status()

    resp_json = resp.json()

    # Check for errors in the response object
    if resp_json.get("error"):
        raise ValueError(f"OpenAI error: {resp_json['error']}")

    # The "output" array can contain multiple items
    # gpt-5 models return: [reasoning block, message block]
    # gpt-4 models return: [message block]
    output_list = resp_json.get("output", [])
    if not output_list:
        raise ValueError("No output in the OpenAI response")

    # Find the message block (skip reasoning blocks)
    message_output = None
    for output_item in output_list:
        if output_item.get("type") == "message":
            message_output = output_item
            break

    # Fall back to first output if no message type found
    if not message_output:
        message_output = output_list[0]

    # Extract text from content array
    content_list = message_output.get("content", [])
    if content_list:
        extracted_text = []
        for content_piece in content_list:
            if content_piece.get("type") == "output_text":
                extracted_text.append(content_piece.get("text", ""))
            elif content_piece.get("type") == "text":
                extracted_text.append(content_piece.get("text", ""))
            elif isinstance(content_piece, str):
                extracted_text.append(content_piece)
        if extracted_text:
            return "".join(extracted_text).strip()

    # Format 2: output[].text (simpler format)
    if message_output.get("text"):
        return message_output.get("text").strip()

    # If nothing worked, log the structure for debugging
    logging.error(f"Unknown response structure: {resp_json}")
    raise ValueError("No content in the message output block")

def setup_logger():
    """
    Sets up a logger to log to both the console and a file in the logs directory.
    
    Returns:
        logger (logging.Logger): Configured logger instance.
    """
    logger = logging.getLogger("RSSFeedMonitor")
    logger.setLevel(logging.INFO)
    
    # Create logs directory if it doesn't exist
    if not os.path.exists("logs"):
        os.makedirs("logs")
    
    # File handler for logging to a file
    file_handler = logging.FileHandler("logs/app.log")
    file_handler.setLevel(logging.INFO)
    
    # Console handler for logging to the console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Formatter to include timestamp, module, level, and message
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add both handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
