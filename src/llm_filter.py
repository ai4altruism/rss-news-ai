# src/llm_filter.py

import logging
import json
import re
from utils import call_responses_api

def sanitize_json_string(json_string):
    """
    Enhanced sanitization of JSON string to fix common issues that cause parsing failures.
    """
    # Remove markdown fences
    json_string = re.sub(r'^```(\w+)?', '', json_string)
    json_string = re.sub(r'```$', '', json_string)
    
    # Handle common truncation issues
    if not json_string.strip().endswith('}'):
        if json_string.count('{') > json_string.count('}'):
            json_string = json_string + '}'
    
    # Fix missing quotes around keys 
    json_string = re.sub(r'([{,]\s*)([a-zA-Z0-9_]+)(\s*:)', r'\1"\2"\3', json_string)
    
    # Fix trailing commas in objects and arrays (common LLM mistake)
    json_string = re.sub(r',\s*}', '}', json_string)
    json_string = re.sub(r',\s*\]', ']', json_string)
    
    # Fix unterminated strings - find strings that begin with " but don't end with " before a comma or closing brace
    lines = json_string.split('\n')
    for i, line in enumerate(lines):
        if '"' in line:
            # Count quotes - if odd number and doesn't end with quote before comma/brace
            if line.count('"') % 2 == 1 and not re.search(r'"[,}\]]?\s*$', line):
                if ',' in line:
                    # Add quote before comma
                    lines[i] = re.sub(r'([^"]*),', r'\1",', line)
                else:
                    # Add quote at end
                    lines[i] = line + '"'
    
    json_string = '\n'.join(lines)
    
    # Handle improperly escaped quotes within JSON strings
    json_string = re.sub(r'(?<!")(?<!\\)"(?![:,}\]])', r'\"', json_string)

    # Ensure we have a complete JSON object
    json_string = json_string.strip()
    
    return json_string

def filter_stories(articles, filter_prompt, filter_model, openai_api_key, batch_size=5):
    """
    Filters articles using an LLM based on a user-specified prompt, in batches.

    Steps:
      1. Chunk the articles into groups of 'batch_size'.
      2. Build a single JSON-based classification prompt for each batch.
      3. Call the LLM once per batch, instructing it to return valid JSON
         with a yes/no decision for each article.
      4. If JSON parsing fails, attempt sanitization and re-parse.
      5. Any article whose decision is 'Yes' gets appended to 'filtered_articles'.

    Parameters:
        articles (list): List of article dictionaries.
        filter_prompt (str): Plain language prompt for filtering.
        filter_model (str): Model name to be used for filtering.
        openai_api_key (str): API key for OpenAI.
        batch_size (int): Number of articles per request.

    Returns:
        filtered_articles (list): List of articles that meet the filter criteria.
    """
    filtered_articles = []

    def chunked(iterable, size):
        for i in range(0, len(iterable), size):
            yield iterable[i : i + size]

    chunk_index = 0
    total_chunks = (len(articles) + batch_size - 1) // batch_size
    for batch in chunked(articles, batch_size):
        chunk_index += 1
        logging.info(f"Processing filter chunk {chunk_index}/{total_chunks}...")

        # Build the prompt with additional criteria.
        article_list_text = ""
        for idx, art in enumerate(batch, start=1):
            title = art.get("title", "").replace("\n", " ")
            # Truncate summary to ~300 chars to avoid huge prompts
            summary_full = art.get("summary", "").replace("\n", " ")
            summary_short = summary_full[:300]
            if len(summary_full) > 300:
                summary_short += "..."

            article_list_text += f"{idx}. Title: {title}\n   Summary: {summary_short}\n\n"

        prompt = f"""
You are evaluating a batch of articles for relevance based on the following criteria:

{filter_prompt}

Additionally, please consider the following additional requirements:
1. **Redundancy Reduction:** Compare each article to any previous similar reports. If the article does not present significant new details or updated facts compared to earlier reports, mark it as "No". If it provides substantial new information, mark it as "Yes".
2. **Generative AI Significance:** Determine whether the reported development or news represents a meaningful advancement or application of generative AI. Exclude articles that only briefly mention generative AI in passing or that discuss AI broadly without specific focus on generative capabilities by marking them as "No".

For each article in this batch, respond with exactly "Yes" or "No" based on both criteria. Return your decisions in valid JSON using the following structure:
{{
  "decisions": [
    {{
      "index": 1,
      "decision": "Yes"
    }},
    ...
  ]
}}

CRITICAL INSTRUCTIONS:
- Return ONLY valid JSON
- Double quotes for all keys and strings
- No trailing commas in arrays or objects
- No single quotes for strings or keys
- No code blocks or markdown, just the JSON object
- No explanation, just plain JSON
- Always close all brackets and braces

Here are the articles in this batch:

{article_list_text}
""".strip()

        try:
            output_text = call_responses_api(
                model=filter_model,
                prompt=prompt,
                openai_api_key=openai_api_key,
                instructions="Output only valid JSON. No extra commentary.",
                max_output_tokens=1024,  # Increase token limit
                temperature=0.0
            )

            # Attempt direct JSON parse
            try:
                parsed = json.loads(output_text)
            except json.JSONDecodeError as e:
                logging.error(f"JSON parsing failed for chunk {chunk_index}: {e}")
                # Attempt to sanitize
                cleaned = sanitize_json_string(output_text)
                try:
                    parsed = json.loads(cleaned)
                except json.JSONDecodeError as e2:
                    logging.error(f"JSON parsing still failed after sanitization for chunk {chunk_index}: {e2}")
                    
                    # One more attempt - try to extract just the decisions array using regex
                    try:
                        decisions_match = re.search(r'"decisions"\s*:\s*\[(.*?)\]', output_text, re.DOTALL)
                        if decisions_match:
                            decisions_json = '{"decisions": [' + decisions_match.group(1) + ']}'
                            cleaned_decisions = sanitize_json_string(decisions_json)
                            parsed = json.loads(cleaned_decisions)
                        else:
                            parsed = {"decisions": []}
                    except Exception:
                        parsed = {"decisions": []}

            # Process decisions
            for dec in parsed.get("decisions", []):
                idx = dec.get("index")
                decision = dec.get("decision", "").lower()
                # Validate index is in range
                if idx and 1 <= idx <= len(batch) and "yes" in decision:
                    filtered_articles.append(batch[idx - 1])

        except Exception as e:
            logging.error(f"LLM filtering error for chunk {chunk_index}: {e}")

    return filtered_articles