import csv
import json
import hashlib
import os
import re
import string
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.pipeline import run_pipeline
from app.lang_utils import mask_terms

PUNCT = re.escape(string.punctuation)

def normalize(text: str) -> str:
    text = re.sub(rf'[{PUNCT}]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def flags_hash(flags) -> str:
    sorted_flags = sorted(flags, key=lambda f: json.dumps(f, sort_keys=True))
    flags_json = json.dumps(sorted_flags, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(flags_json.encode('utf-8')).hexdigest()

def test_golden_regression():
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    inp_path = os.path.join(data_dir, 'golden_inputs.csv')
    exp_path = os.path.join(data_dir, 'golden_expected.jsonl')

    with open(exp_path, encoding='utf-8') as f:
        expected = {int(obj['id']): obj for obj in map(json.loads, f)}

    with open(inp_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rid = int(row['id'])
            text = row['text']
            terms = [t.strip() for t in row['protected_terms'].split('|')] if row['protected_terms'] else []
            translate = row['translate_embedded'].strip().lower() == 'true'
            result = run_pipeline(text, translate_embedded=translate, protected_terms=terms)

            # compare flags
            assert flags_hash(result['flags']) == expected[rid]['flags_hash']

            # normalized text comparison
            assert normalize(result['clean_text']) == normalize(expected[rid]['clean_text'])

            # invariants: numbers and protected terms
            masked_input = mask_terms(text, terms)
            for num in re.findall(r'-?\d+(?:[.,]\d+)?', masked_input):
                assert num in result['clean_text']
            for term in re.findall(r'<TERM>(.*?)</TERM>', masked_input):
                assert f'<TERM>{term}</TERM>' in result['clean_text']
