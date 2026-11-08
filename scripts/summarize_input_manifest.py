#!/usr/bin/env python3
"""Emit allowlisted aggregate CSV metadata, never original paths or image content.

This does not score images, validate image files, or measure reconstruction success.
"""
import argparse
from collections import Counter
import csv
import json
import math
from pathlib import Path
import sys

REQUIRED = {'suggested_key', 'quality_score', 'width', 'height', 'image_format', 'selected'}

def read_rows(path, required):
    if Path(path).stat().st_size > 50 * 1024 * 1024:
        raise ValueError('CSV exceeds the 50 MiB review limit')
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if not required.issubset(reader.fieldnames or []):
            raise ValueError('CSV lacks required columns')
        return list(reader)

def summarize(rows, candidates):
    keys = [r.get('suggested_key', '') for r in rows]
    picked = [r.get('suggested_key', '') for r in candidates]
    keyset = set(keys) - {''}
    scores, invalid_score, invalid_size = [], 0, 0
    for row in rows:
        try:
            score = float(row.get('quality_score', ''))
            if not math.isfinite(score):
                raise ValueError
            scores.append(score)
        except (ValueError, TypeError):
            invalid_score += 1
        try:
            if int(row.get('width', '0')) <= 0 or int(row.get('height', '0')) <= 0:
                raise ValueError
        except (ValueError, TypeError):
            invalid_size += 1
    selected = {r.get('suggested_key') for r in rows if r.get('selected') == 'YES'} - {None, ''}
    flags = Counter(r.get('selected') if r.get('selected') in {'YES', 'NO'} else 'OTHER' for r in rows)
    formats = Counter(r.get('image_format') if r.get('image_format') in {'JPEG', 'PNG'} else 'OTHER' for r in rows)
    return {
        'scope': 'CSV records only; no image-byte or reconstruction validation',
        'manifest_rows': len(rows),
        'candidate_rows': len(candidates),
        'unique_nonempty_manifest_keys': len(keyset),
        'unique_nonempty_candidate_keys': len(set(picked) - {''}),
        'empty_manifest_keys': keys.count(''),
        'empty_candidate_keys': picked.count(''),
        'duplicate_manifest_key_rows': len(keys) - len(set(keys)),
        'duplicate_candidate_key_rows': len(picked) - len(set(picked)),
        'candidate_keys_missing_from_manifest': len((set(picked) - {''}) - keyset),
        'candidate_keys_equal_selected_yes_keys': (set(picked) - {''}) == selected,
        'selected_flags': dict(sorted(flags.items())),
        'image_formats_from_metadata': dict(sorted(formats.items())),
        'invalid_score_rows': invalid_score,
        'invalid_dimension_rows': invalid_size,
        'declared_score_min': min(scores) if scores else None,
        'declared_score_max': max(scores) if scores else None,
        'privacy': 'No source names, paths, per-image identifiers, reasons, thumbnails, or EXIF are emitted',
    }

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--candidates', required=True)
    args = parser.parse_args(argv)
    try:
        rows = read_rows(args.manifest, REQUIRED)
        candidates = read_rows(args.candidates, {'suggested_key'})
        result = summarize(rows, candidates)
    except (OSError, UnicodeError, ValueError, csv.Error):
        print('Input CSV could not be read or does not match the required schema.', file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0

if __name__ == '__main__':
    sys.exit(main())
