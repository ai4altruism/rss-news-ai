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
    data = {
        "model": model,
        "input": prompt,
        "temperature": temperature,
        "max_output_tokens": max_output_tokens
    }
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

    # The "output" array can contain multiple items; typically we just grab the first
    output_list = resp_json.get("output", [])
    if not output_list:
        raise ValueError("No output in the OpenAI response")

    content_list = output_list[0].get("content", [])
    if not content_list:
        raise ValueError("No content in the first output block")

    # Extract the text
    extracted_text = []
    for content_piece in content_list:
        if content_piece.get("type") == "output_text":
            extracted_text.append(content_piece.get("text", ""))

    return "".join(extracted_text).strip()

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
