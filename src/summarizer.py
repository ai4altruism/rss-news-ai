# src/summarizer.py

import logging
import json
import re
from utils import call_llm

def sanitize_json_string(json_string):
    """
    Enhanced sanitization of JSON string to fix common issues that cause parsing failures.
    """
    # Remove any markdown artifacts
    json_string = re.sub(r'^```json\s*', '', json_string)
    json_string = re.sub(r'^```\s*', '', json_string)
    json_string = re.sub(r'\s*```$', '', json_string)
    
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
    if not json_string.startswith('{'):
        json_string = '{' + json_string
    if not json_string.endswith('}'):
        json_string = json_string + '}'
        
    return json_string

def validate_json(json_string):
    """
    Attempt to validate and fix JSON if possible.

    Returns:
        (is_valid: bool, result: dict or str)
    """
    try:
        parsed = json.loads(json_string)
        return True, parsed
    except json.JSONDecodeError as e:
        logging.warning(f"Initial JSON parsing failed: {e}")

        # First sanitization attempt
        sanitized = sanitize_json_string(json_string)
        try:
            parsed = json.loads(sanitized)
            logging.info("JSON sanitization resolved parsing issues")
            return True, parsed
        except json.JSONDecodeError as e:
            logging.error(f"JSON parsing still failed after sanitization: {e}")
            
            # Final fallback - attempt to extract any valid JSON object
            try:
                # Look for patterns like {"topics": [...]} or {topics: [...]}
                pattern = r'\{[\s\S]*"topics"[\s\S]*\}'
                match = re.search(pattern, sanitized)
                if match:
                    extract = match.group(0)
                    # Try to fix and parse this extracted content
                    extract_fixed = sanitize_json_string(extract)
                    parsed = json.loads(extract_fixed)
                    logging.info("Extracted partial JSON object with 'topics' key")
                    return True, parsed
            except (json.JSONDecodeError, AttributeError) as e2:
                logging.error(f"Final JSON extraction attempt failed: {e2}")
            
            return False, str(e)

def unify_topics(topics_list):
    """
    Merge topics with the same name into a single topic entry.
    Deduplicate articles in the process.
    """
    unified = {}
    for topic_dict in topics_list:
        topic_name = topic_dict.get("topic", "Untitled").strip()
        if topic_name not in unified:
            unified[topic_name] = {
                "topic": topic_name,
                "articles": []
            }
        # Combine articles
        for article in topic_dict.get("articles", []):
            if article not in unified[topic_name]["articles"]:
                unified[topic_name]["articles"].append(article)
    return list(unified.values())

def group_and_summarize(articles, group_model, summarize_model, openai_api_key):
    """
    Groups articles by topic and generates summaries using OpenAI's Responses API,
    preserving hyperlinks. Unifies topic labels across chunks.
    
    Parameters:
        articles (list): List of filtered article dictionaries.
        group_model (str): Model name for grouping articles.
        summarize_model (str): Model name for summarizing groups.
        openai_api_key (str): API key for OpenAI.

    Returns:
        dict: A structured JSON-like dict with topic groups, summaries, and article links.
    """

    if not articles:
        return {"topics": []}

    def chunk_articles(articles_list, chunk_size=10):
        """Split articles into smaller chunks to avoid token limits."""
        for i in range(0, len(articles_list), chunk_size):
            yield articles_list[i:i + chunk_size]

    all_topics = []

    # ----------------------
    # GROUPING PHASE
    # ----------------------
    for chunk_index, article_chunk in enumerate(chunk_articles(articles, 10)):
        logging.info(f"Processing article chunk {chunk_index + 1} for grouping...")

        # Build the text snippet for each article in this chunk
        articles_text = "\n\n".join([
            f"Title: {json.dumps(a.get('title'))}, Link: {json.dumps(a.get('link'))}"
            for a in article_chunk
        ])

        # Improved prompt to emphasize JSON validation
        group_prompt = f"""
Group these articles into topics focused on generative AI. Return ONLY valid JSON in this exact format:
{{
    "topics": [
        {{
            "topic": "Topic Name",
            "articles": [
                {{"title": "Article Title", "link": "Article Link"}}
            ]
        }}
    ]
}}

CRITICAL INSTRUCTIONS:
- Return ONLY valid JSON
- Double quotes for all keys and strings 
- No trailing commas in arrays or objects (e.g., [1, 2,] or {{"name": "value",}})
- No single quotes for strings or keys
- No code blocks or markdown, just the JSON object
- No explanation, just plain JSON
- Always close all brackets and braces
- Make sure each key-value pair ends with a comma except the last one

Here are the articles to group:
{articles_text}
"""

        try:
            # Call the new Responses API for grouping
            group_raw_output = call_llm(
                model_config=group_model,
                prompt=group_prompt,
                api_keys={"openai": openai_api_key},
                instructions="You are a JSON formatting expert who organizes articles into topics about generative AI.",
                max_tokens=4000,
                temperature=0.0,
                task_type="group"
            )

            # Attempt direct JSON parse
            try:
                parsed = json.loads(group_raw_output)
                all_topics.extend(parsed.get("topics", []))
            except json.JSONDecodeError:
                # Attempt to fix
                is_valid, result = validate_json(group_raw_output)
                if is_valid:
                    all_topics.extend(result.get("topics", []))
                else:
                    logging.error(f"JSON validation failed on chunk {chunk_index + 1}: {result}")
                    fallback = {
                        "topic": f"Generative AI Articles Group {chunk_index+1}",
                        "articles": [
                            {"title": a.get("title"), "link": a.get("link")} for a in article_chunk
                        ]
                    }
                    all_topics.append(fallback)

        except Exception as e:
            logging.error(f"LLM grouping error for chunk {chunk_index+1}: {e}")
            fallback_topic = {
                "topic": f"Generative AI Articles Group {chunk_index+1}",
                "articles": [{"title": a.get("title", ""), "link": a.get("link", "")} for a in article_chunk]
            }
            all_topics.append(fallback_topic)

    # ----------------------
    # UNIFY TOPICS
    # ----------------------
    unified_topics = unify_topics(all_topics)

    # ----------------------
    # SUMMARIZATION PHASE
    # ----------------------
    for topic in unified_topics:
        articles_in_topic = topic.get("articles", [])

        if not articles_in_topic:
            topic["summary"] = "No articles available for summarization."
            continue

        # Match each short-article dict to the full article in 'articles' to retrieve summary
        relevant_articles = []
        for stub in articles_in_topic:
            match = next((a for a in articles if a.get("title") == stub.get("title")), None)
            if match:
                relevant_articles.append(match)
            else:
                relevant_articles.append({
                    "title": stub.get("title", ""),
                    "link": stub.get("link", ""),
                    "summary": "No detailed summary available."
                })

        # Build a combined prompt text from up to 5 articles
        combined_text = "\n\n".join([
            f"Title: {a.get('title')}, Summary: {a.get('summary') or ''}"
            for a in relevant_articles[:5]
        ])

        if not combined_text.strip():
            topic["summary"] = f"A collection of {len(articles_in_topic)} articles about {topic.get('topic')}."
            continue

        summarize_prompt = f"""
Summarize these articles about "{topic.get('topic')}" in ONE concise paragraph, focusing on key developments in generative AI:

{combined_text}

RESPONSE FORMAT: Just one short paragraph.
"""

        try:
            summary_text = call_llm(
                model_config=summarize_model,
                prompt=summarize_prompt,
                api_keys={"openai": openai_api_key},
                instructions="You create brief, informative summaries of generative AI news articles in a single paragraph.",
                max_tokens=250,
                temperature=0.5,
                task_type="summarize"
            )

            # Basic cleanup
            summary_text = re.sub(r'\s+', ' ', summary_text).strip()
            if not summary_text:
                summary_text = f"A collection of {len(articles_in_topic)} articles about {topic.get('topic')}."
            topic["summary"] = summary_text

        except Exception as e:
            logging.error(f"LLM summarization error for topic '{topic.get('topic')}': {e}")
            topic["summary"] = f"A collection of {len(articles_in_topic)} articles about {topic.get('topic')}."

        # Restore the final article array with minimal keys
        topic["articles"] = [{"title": s.get("title", "Untitled"), "link": s.get("link", "#")} for s in articles_in_topic]

    return {"topics": unified_topics}