# Tests

Run the suite (no network, no real API calls):

    python -m pytest
    python -m pytest --cov=src --cov-report=term

Install dev dependencies with `pip install -r requirements.txt -r requirements-dev.txt`.

## Known bugs are pinned with strict xfail

A verified bug that is not fixed yet appears as
`@known_bug("one-line reason")` (from `tests/fakes.py`), which is
`pytest.mark.xfail(strict=True, reason="BUG: ...")`. The test asserts the
*correct* behavior and is reported as `xfailed` today. When someone fixes the
bug the test XPASSes, which strict mode turns into a failure: delete the
marker and the test becomes a normal regression test.

List them with `python -m pytest -rx -q`.

## Prompt snapshots

`tests/snapshots/*.txt` hold the exact filter, group, summarize and query
prompts. An intentional prompt change fails `tests/test_prompt_snapshots.py`
with a diff; accept it with `UPDATE_SNAPSHOTS=1 python -m pytest
tests/test_prompt_snapshots.py` and review the resulting git diff.

## Conventions

- Provider HTTP is stubbed by patching `requests.post` in the provider module.
- LLM calls are stubbed by patching `call_llm` where it is imported.
- Database tests use a temporary SQLite file (`tmp_path`); time is moved by
  back-dating rows, never by sleeping.
