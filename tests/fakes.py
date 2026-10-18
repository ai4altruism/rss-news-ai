# tests/fakes.py
"""
Small shared helpers for the unit-harness tests: a fake HTTP response,
a snapshot assertion, and a pytest marker factory for known bugs.

No test here touches the network; every provider test patches
``requests.post`` at the provider module.
"""

import difflib
import json
import os
from unittest.mock import MagicMock

import pytest

SNAPSHOT_DIR = os.path.join(os.path.dirname(__file__), "snapshots")


def fake_response(payload, status_code=200):
    """Build a stand-in for requests.Response carrying a JSON body."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = status_code < 400
    resp.json.return_value = payload
    resp.text = json.dumps(payload)
    return resp


def known_bug(reason):
    """xfail(strict) marker for a verified bug. strict=True makes the test
    fail loudly (XPASS) the moment the bug is fixed, so the marker gets removed."""
    return pytest.mark.xfail(strict=True, reason=f"BUG: {reason}")


def assert_matches_snapshot(name, text):
    """Compare text with tests/snapshots/<name>.txt.

    Set UPDATE_SNAPSHOTS=1 to (re)write the file after an intentional
    prompt change; the resulting git diff is the review artifact.
    """
    path = os.path.join(SNAPSHOT_DIR, f"{name}.txt")
    if os.environ.get("UPDATE_SNAPSHOTS") == "1":
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return
    assert os.path.exists(path), (
        f"Missing snapshot {path}; run with UPDATE_SNAPSHOTS=1 to create it"
    )
    with open(path, encoding="utf-8") as f:
        expected = f.read()
    if text != expected:
        diff = "\n".join(difflib.unified_diff(
            expected.splitlines(), text.splitlines(),
            "snapshot", "actual", lineterm="",
        ))
        pytest.fail(f"Prompt changed vs snapshot {name}.txt "
                    f"(UPDATE_SNAPSHOTS=1 to accept):\n{diff}")
