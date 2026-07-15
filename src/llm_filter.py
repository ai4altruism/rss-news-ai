# src/llm_filter.py

import logging
import json
import re
from utils import call_llm
from json_utils import validate_json

def filter_stories(articles, filter_prompt, filter_model, openai_api_key, batch_size=5):
    """
    Filters articles using an LLM based on a user-specified prompt, in batches.

    Steps:
      1. Chunk the articles into groups of 'batch_size'.
      2. Build a single JSON-based classification prompt for each batch.
      3. Call the LLM once per batch, instructing it to return valid JSON
         with a yes/no decision for each article.
      4. If JSON parsing fails, attempt safe recovery and re-parse.
      5. Sort each article into accepted / rejected / errored by decision.

    Every input article lands in exactly one of the three returned lists,
    so the caller can record rejections (suppress reprocessing) while
    leaving errored articles unrecorded (retried next run).

    Parameters:
        articles (list): List of article dictionaries.
        filter_prompt (str): Plain language prompt for filtering.
        filter_model (str): Model name to be used for filtering.
        openai_api_key (str): API key for OpenAI.
        batch_size (int): Number of articles per request.

    Returns:
        (accepted, rejected, errored): Three lists of article dicts.
            accepted — LLM said "Yes"
            rejected — LLM said "No"
            errored  — the LLM call failed, its output was unparseable, or
                       its decisions omitted the article
    """
    accepted = []
    rejected = []
    errored = []

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
- Include a decision for EVERY article, indices 1 through {len(batch)}

Here are the articles in this batch:

{article_list_text}
""".strip()

        parsed = None
        try:
            output_text = call_llm(
                model_config=filter_model,
                prompt=prompt,
                api_keys={"openai": openai_api_key},
                instructions="Output only valid JSON. No extra commentary.",
                max_tokens=1024,
                temperature=0.0,
                task_type="filter"
            )

            if not output_text or not output_text.strip():
                raise ValueError("Empty response from filter model")

            is_valid, result = validate_json(output_text)
            if is_valid:
                parsed = result
            else:
                # Last resort: extract just the decisions array. Safe here
                # because decision entries contain no free text, only
                # index/decision pairs.
                decisions_match = re.search(
                    r'"decisions"\s*:\s*\[(.*?)\]', output_text, re.DOTALL
                )
                if decisions_match:
                    rebuilt = '{"decisions": [' + decisions_match.group(1) + ']}'
                    # Trailing-comma repair is safe here (unlike on free text)
                    # because decision entries contain no prose
                    rebuilt = re.sub(r',\s*([\]}])', r'\1', rebuilt)
                    try:
                        parsed = json.loads(rebuilt)
                    except json.JSONDecodeError:
                        parsed = None
                if parsed is None:
                    logging.error(
                        f"Unparseable filter response for chunk {chunk_index}; "
                        f"articles will be retried next run."
                    )

        except Exception as e:
            logging.error(f"LLM filtering error for chunk {chunk_index}: {e}")

        if parsed is None:
            errored.extend(batch)
            continue

        # Sort articles by decision; anything the LLM omitted or answered
        # ambiguously counts as errored so it retries next run.
        decisions_by_index = {}
        for dec in parsed.get("decisions", []):
            idx = dec.get("index")
            # LLMs sometimes emit indices as JSON strings
            if isinstance(idx, str) and idx.strip().isdigit():
                idx = int(idx.strip())
            if isinstance(idx, int) and 1 <= idx <= len(batch):
                decisions_by_index[idx] = (
                    str(dec.get("decision", "")).strip().strip('."\'').lower()
                )

        for idx, article in enumerate(batch, start=1):
            decision = decisions_by_index.get(idx)
            # Word-boundary match: accepts verbose forms like
            # "Yes, highly relevant" but not e.g. "none" as a "no"
            if decision is not None and re.match(r'yes\b', decision):
                accepted.append(article)
            elif decision is not None and re.match(r'no\b', decision):
                rejected.append(article)
            else:
                logging.warning(
                    f"No usable decision for article {idx} in chunk {chunk_index}; "
                    f"will retry next run: {article.get('title', 'Untitled')!r}"
                )
                errored.append(article)

    return accepted, rejected, errored
