# src/summarizer.py

import logging
import json
import re
from utils import call_llm
from json_utils import validate_json

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
    Groups articles by topic and generates summaries, preserving hyperlinks.
    Unifies topic labels across chunks.

    Titles/links in the LLM's grouping output are treated as lookup keys
    only: each is grounded back to a source article and the published
    output carries source data verbatim, so a paraphrased title or
    corrupted link can never reach Slack/email/web. Articles the LLM
    omits from its grouping response land in a catch-all topic instead
    of vanishing.

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
- Copy each title and link EXACTLY as given; include every article exactly once

Here are the articles to group:
{articles_text}
"""

        try:
            group_raw_output = call_llm(
                model_config=group_model,
                prompt=group_prompt,
                api_keys={"openai": openai_api_key},
                instructions="You are a JSON formatting expert who organizes articles into topics about generative AI.",
                max_tokens=4000,
                temperature=0.0,
                task_type="group"
            )

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
    # GROUNDING PHASE
    # ----------------------
    # Ground every LLM-emitted article back to a source article. The LLM can
    # paraphrase titles or corrupt links when echoing them, so titles/links in
    # its output are lookup keys only — the published output always carries
    # source data.
    def _normalize_title(title):
        return re.sub(r"\s+", " ", (title or "").strip().lower())

    by_link = {a.get("link"): a for a in articles if a.get("link")}
    by_title = {a.get("title"): a for a in articles if a.get("title")}
    by_norm_title = {_normalize_title(a.get("title")): a for a in articles if a.get("title")}

    grounded_topics = []
    placed_ids = set()
    for topic in unified_topics:
        grounded = []
        for stub in topic.get("articles", []):
            src = (
                by_link.get(stub.get("link"))
                or by_title.get(stub.get("title"))
                or by_norm_title.get(_normalize_title(stub.get("title")))
            )
            if src is None:
                logging.warning(
                    f"Dropping ungroundable article from topic '{topic.get('topic')}': "
                    f"{stub.get('title')!r}"
                )
                continue
            if id(src) in placed_ids:
                continue  # already placed in an earlier topic
            placed_ids.add(id(src))
            grounded.append(src)
        if grounded:
            grounded_topics.append((topic, grounded))
        else:
            logging.warning(
                f"Dropping topic with no groundable articles: '{topic.get('topic')}'"
            )

    # Articles the LLM omitted from its grouping response would otherwise
    # never appear in a report even though the filter accepted them —
    # collect them into a catch-all topic instead of losing them.
    leftovers = [a for a in articles if id(a) not in placed_ids]
    if leftovers:
        logging.warning(
            f"{len(leftovers)} article(s) missing from LLM grouping; adding catch-all topic."
        )
        grounded_topics.append(({"topic": "Additional stories"}, leftovers))

    # ----------------------
    # SUMMARIZATION PHASE
    # ----------------------
    output_topics = []
    for topic, relevant_articles in grounded_topics:
        # Output articles come straight from source data
        topic["articles"] = [
            {"title": a.get("title", "Untitled"), "link": a.get("link", "#")}
            for a in relevant_articles
        ]

        # Build a combined prompt text from up to 5 articles
        combined_text = "\n\n".join([
            f"Title: {a.get('title')}, Summary: {a.get('summary') or ''}"
            for a in relevant_articles[:5]
        ])

        if not combined_text.strip():
            topic["summary"] = f"A collection of {len(relevant_articles)} articles about {topic.get('topic')}."
            output_topics.append(topic)
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
                summary_text = f"A collection of {len(relevant_articles)} articles about {topic.get('topic')}."
            topic["summary"] = summary_text

        except Exception as e:
            logging.error(f"LLM summarization error for topic '{topic.get('topic')}': {e}")
            topic["summary"] = f"A collection of {len(relevant_articles)} articles about {topic.get('topic')}."

        output_topics.append(topic)

    return {"topics": output_topics}
