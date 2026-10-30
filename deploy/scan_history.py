"""Heuristic history scan. Prints locations/fingerprints only, never matched text.

Run: python deploy/scan_history.py
Exit 1 means candidates need review (not proof that a credential was exposed).
Includes removed lines and every parent of merge commits in all locally fetched refs.
"""
from __future__ import annotations

import base64
import collections
import hashlib
import json
import math
import re
import subprocess

PATTERNS = {
    'google_key': re.compile(r'AIza[A-Za-z0-9_-]{20,}'),
    'openai_key': re.compile(r'\bsk-[A-Za-z0-9_-]{16,}'),
    'webhook_secret': re.compile(r'\bwhsec_[A-Za-z0-9+/=_-]{16,}'),
    'slack_token': re.compile(r'\bxox[baprs]-[A-Za-z0-9-]{16,}'),
    'github_token': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})'),
    'telegram_token': re.compile(r'\b[0-9]{6,12}:[A-Za-z0-9_-]{30,}'),
    'private_key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'base64': re.compile(r'(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{40,}={0,2}(?![A-Za-z0-9+/])'),
}
# Exact public Standard Webhooks test vectors, reviewed against upstream test_sign_function.
# No whole-file or whole-directory exemption: a different value still fails.
PUBLIC_TEST_VECTORS = {
    ('backend/tests/test_payments.py', 'webhook_secret', '96ad2ccd81462a76'),
    ('backend/tests/test_payments.py', 'base64', 'b186714e50f982f9'),
}


def git(*args):
    return subprocess.check_output(['git', *args]).decode('utf-8', errors='replace')


def entropy(value):
    return -sum((n / len(value)) * math.log2(n / len(value)) for n in collections.Counter(value).values())


def scan():
    patch = git('log', '--all', '--full-history', '-m', '--no-ext-diff', '--no-renames',
                '--format=SCAN_COMMIT:%H', '-p')
    found = {}
    prefix_counts = collections.Counter()
    commit, path, line_number = '', '', 0
    for line in patch.splitlines():
        if line.startswith('SCAN_COMMIT:'):
            commit = line.split(':', 1)[1]
        elif line.startswith('diff --git '):
            path = line.split(' b/', 1)[-1]
            line_number = 0
        elif line.startswith('@@ '):
            match = re.search(r'\+(\d+)', line)
            line_number = int(match[1]) - 1 if match else 0
        elif line[:1] in ('+', '-', ' ') and not line.startswith(('+++', '---')):
            if line[0] != '-':
                line_number += 1
            for prefix in ('AIza', 'sk-', 'whsec_', 'xox', 'ghp_'):
                prefix_counts[prefix] += line.count(prefix)
            for kind, pattern in PATTERNS.items():
                for match in pattern.finditer(line[1:]):
                    value = match[0]
                    if kind == 'base64' and (re.fullmatch('[a-fA-F0-9]+', value) or entropy(value) < 4.2):
                        continue
                    fingerprint = hashlib.sha256(value.encode()).hexdigest()[:16]
                    key = (path, kind, fingerprint)
                    if key in found:
                        continue
                    media = False
                    if kind == 'base64':
                        try:
                            raw = base64.b64decode(value + '=' * (-len(value) % 4), validate=True)
                            media = raw.startswith((b'\x89PNG\r\n', b'\xff\xd8\xff', b'RIFF', b'OggS'))
                        except ValueError:
                            pass
                    found[key] = dict(path=path, commit=commit, patch_line=line_number, kind=kind,
                                      length=len(value), fingerprint=fingerprint,
                                      classification=('public test vector' if key in PUBLIC_TEST_VECTORS else
                                                      'embedded media; review metadata' if media else 'review required'))
    env_paths = sorted(set(p for p in git('log', '--all', '--format=', '--name-only', '--full-history', '-m').splitlines()
                           if p.rsplit('/', 1)[-1] in ('.env', '.env.railway')))
    return dict(commits=int(git('rev-list', '--all', '--count')), head=git('rev-parse', 'HEAD').strip(),
                refs=git('for-each-ref', '--format=%(refname) %(objectname)').splitlines(),
                forbidden_env_paths=env_paths, prefix_occurrences=dict(prefix_counts), candidates=list(found.values()))


if __name__ == '__main__':
    result = scan()
    print(json.dumps(result, indent=2))
    raise SystemExit(int(bool(result['forbidden_env_paths']) or
                         any(c['classification'] == 'review required' for c in result['candidates'])))
