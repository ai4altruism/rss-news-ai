# src/json_utils.py

"""
Shared JSON handling for LLM responses.

Replaces the per-module sanitize_json_string implementations whose regex
"repairs" (re-escaping quotes mid-string, quoting bare keys, appending a
quote to any line with an odd quote count) could corrupt valid JSON whose
strings legitimately contain quotes. Only safe, non-mutating recovery
steps are kept: markdown-fence stripping and outermost-object extraction.
"""

import json
import logging
import re


def sanitize_json_string(json_string):
    """
    Strip markdown code fences (```json ... ```) that LLMs sometimes wrap
    around JSON output.

    Deliberately does nothing else: every caller has a structural fallback
    when parsing fails (the filter retries articles next run, the grouper
    lists raw articles), so heavier regex "repairs" are not worth the risk
    of corrupting valid output.

    Parameters:
        json_string (str): Potentially fence-wrapped JSON string

    Returns:
        str: JSON string without markdown fences
    """
    json_string = json_string.strip()
    json_string = re.sub(r'^```(?:json)?\s*', '', json_string)
    json_string = re.sub(r'\s*```$', '', json_string)
    return json_string


def validate_json(json_string):
    """
    Attempt to parse a JSON string, recovering with safe transforms only.

    Recovery steps, in order:
      1. Parse as-is.
      2. Strip markdown fences and re-parse.
      3. Extract the outermost {...} span and parse that (handles prose
         before/after the JSON object without mutating its contents).

    Returns:
        (is_valid: bool, result: dict or error string)
    """
    try:
        return True, json.loads(json_string)
    except json.JSONDecodeError as e:
        first_error = e

    sanitized = sanitize_json_string(json_string)
    try:
        parsed = json.loads(sanitized)
        logging.info("JSON parsed after markdown-fence stripping")
        return True, parsed
    except json.JSONDecodeError:
        pass

    start = sanitized.find('{')
    end = sanitized.rfind('}')
    if start != -1 and end > start:
        try:
            parsed = json.loads(sanitized[start:end + 1])
            logging.info("JSON parsed after extracting outermost object")
            return True, parsed
        except json.JSONDecodeError:
            pass

    logging.error(f"JSON parsing failed after all recovery attempts: {first_error}")
    return False, str(first_error)
