"""No unlabelled phone/UPI-shaped values in shipped examples and seed text."""
import json
import re

import pytest

from backend.config import ROOT
from backend.extraction import PHONE, UPI


def unsafe_text(text):
    return '(sample)' not in text.lower() and bool(
        PHONE.search(text) or re.search(r'(?<!\w)\d{10}(?!\w)', text) or UPI.search(text))


def strings(value, location='$'):
    if isinstance(value, dict):
        for key, item in value.items():
            yield f'{location} key', str(key)
            yield from strings(item, f'{location}.{key}')
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from strings(item, f'{location}[{index}]')
    elif isinstance(value, (str, int)):
        yield location, str(value)


def test_shipped_samples_are_labelled():
    failures = []
    for folder in ('examples', 'seed'):
        for path in sorted((ROOT / folder).rglob('*')):
            if not path.is_file() or '__pycache__' in path.parts:
                continue
            try:
                text = path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                # Binary media needs the manual consent/redaction review in docs/COLLECT.md.
                continue
            if path.suffix == '.json':
                leaves = strings(json.loads(text))
            elif path.suffix == '.jsonl':
                leaves = ((f'line {i} {loc}', value) for i, line in enumerate(text.splitlines(), 1)
                          if line.strip() for loc, value in strings(json.loads(line)))
            else:
                leaves = ((f'line {i}', line) for i, line in enumerate(text.splitlines(), 1))
            failures.extend(f'{path.relative_to(ROOT)} {loc}' for loc, value in leaves if unsafe_text(value))
    # Locations only: don't leak an accidentally committed real identifier into CI logs.
    assert not failures, 'Unlabelled identifier-shaped sample text at: ' + ', '.join(failures)


@pytest.mark.parametrize('text, unsafe', [
    ('Contact 9876543210', True), ('UPI desk@ybl', True),
    ('(sample) Contact 9876543210', False), ('desk@ybl (sample)', False),
    ('Contact de…@ybl or 98xxxxxx10', False), ('support@example.com', False),
])
def test_sample_guard(text, unsafe):
    assert unsafe_text(text) is unsafe
