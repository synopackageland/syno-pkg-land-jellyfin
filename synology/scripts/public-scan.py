#!/usr/bin/env python3
"""Scan integration files and optional artifact trees without printing matches."""
import argparse
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--denylist', default=os.environ.get('SPL_INTERNAL_DENYLIST'))
parser.add_argument('--artifacts', action='append', default=[])
parser.add_argument('--message')
args = parser.parse_args()
if not args.denylist:
    raise SystemExit('Set SPL_INTERNAL_DENYLIST to the private operator denylist')
denied = [line for line in Path(args.denylist).read_bytes().splitlines() if line]
pattern = re.compile('|'.join([
    't-' + '[0-9]{4}', 'redac' + 'ted', 'redac' + 'ted', 'redac' + 'ted',
    'redac' + 'ted', 'redac' + 'ted', 'redac' + 'ted', 'redac' + 'ted',
    'redac' + 'ted', 'redac' + 'ted', 'redac' + 'ted',
    'redac' + 'ted', 'redac' + 'ted', r'synology' + r'\.com', 'redac' + 'ted',
    r'gh[pousr]_[A-Za-z0-9]{20,}', r'github_pat_[A-Za-z0-9_]{20,}',
    r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',
]).encode())
ignored = {'node_modules', '.artifacts', '.synopkgland', '.e2e', 'evidence', 'dist', '.cache', '__pycache__'}
files = [p for p in ROOT.rglob('*') if p.is_file() and not (set(p.relative_to(ROOT).parts) & ignored)]
for directory in args.artifacts:
    files.extend(p for p in Path(directory).rglob('*') if p.is_file())
if args.message:
    files.append(Path(args.message))
failed = []
for file in files:
    data = file.read_bytes()
    if pattern.search(data) or any(value in data for value in denied):
        failed.append(str(file.relative_to(ROOT)) if file.is_relative_to(ROOT) else file.name)
if failed:
    raise SystemExit('Public scan rejected: ' + ', '.join(sorted(set(failed))))
print(f'Public content scan passed ({len(files)} files; denylist matches never printed).')
