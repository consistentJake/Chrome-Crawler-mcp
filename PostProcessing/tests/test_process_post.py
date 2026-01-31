import json
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from process_json import process_post


def load_test_json(filename: str):
    path = Path(__file__).with_name(filename)
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def test_process_post_builds_expected_hierarchy(capsys: pytest.CaptureFixture[str]):
    post_data = load_test_json("test_post_input.json")
    expected = load_test_json("test_post_expected_output.json")
    actual = process_post(post_data)

    with capsys.disabled():
        print("Actual output:\n", json.dumps(actual, ensure_ascii=False, indent=2))

    assert actual == expected
