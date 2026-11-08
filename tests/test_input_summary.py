"""Synthetic aggregate-parser tests; no real images or external services."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('summary', Path(__file__).resolve().parents[1] / 'scripts/summarize_input_manifest.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def row(key='a', selected='YES', **kw):
    return dict(suggested_key=key, quality_score='90', width='640', height='480', image_format='JPEG', selected=selected, **kw)

class InputSummaryTests(unittest.TestCase):
    def test_valid_counts(self):
        d = m.summarize([row(), row('b','NO')], [{'suggested_key':'a'}])
        self.assertEqual((d['manifest_rows'], d['candidate_rows']), (2, 1))
        self.assertTrue(d['candidate_keys_equal_selected_yes_keys'])
    def test_no_private_fields(self):
        d = m.summarize([row(original_path='/private/example-person/photo.jpg', filename='private-person.jpg', reason='private note')], [{'suggested_key':'a'}])
        s = json.dumps(d)
        for x in ['example-person', 'private-person', 'private note']:
            self.assertNotIn(x, s)
    def test_unexpected_format_not_echoed(self):
        r=row();r['image_format']='secret string';r['selected']='private flag'
        s=json.dumps(m.summarize([r],[]))
        self.assertNotIn('secret string',s);self.assertNotIn('private flag',s)
        self.assertIn('OTHER',s)
    def test_missing_candidate(self):
        d=m.summarize([row()],[{'suggested_key':'missing'}])
        self.assertEqual(d['candidate_keys_missing_from_manifest'],1)
        self.assertFalse(d['candidate_keys_equal_selected_yes_keys'])
    def test_duplicate_counts(self):
        d=m.summarize([row(),row()],[{'suggested_key':'a'},{'suggested_key':'a'}])
        self.assertEqual(d['duplicate_manifest_key_rows'],1)
        self.assertEqual(d['duplicate_candidate_key_rows'],1)
    def test_nan_and_dimensions(self):
        r=row();r['quality_score']='NaN';r['width']='invalid'
        d=m.summarize([r],[])
        self.assertEqual(d['invalid_score_rows'],1);self.assertEqual(d['invalid_dimension_rows'],1)
        self.assertIsNone(d['declared_score_min'])
        json.dumps(d,allow_nan=False)
    def test_empty(self):
        d=m.summarize([],[])
        self.assertEqual(d['manifest_rows'],0);self.assertIsNone(d['declared_score_max'])
    def test_schema_error_no_path_echo(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'private-name.csv';p.write_text('bad\nvalue\n')
            out=io.StringIO()
            with contextlib.redirect_stderr(out):
                rc=m.main(['--manifest',str(p),'--candidates',str(p)])
            self.assertEqual(rc,1);self.assertNotIn(t,out.getvalue());self.assertNotIn('private-name',out.getvalue())
    def test_utf8_bom_csv(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'test.csv';p.write_text('\ufeffsuggested_key,quality_score,width,height,image_format,selected\na,90,640,480,JPEG,YES\n')
            self.assertEqual(len(m.read_rows(p,m.REQUIRED)),1)
    def test_empty_key_count(self):
        d=m.summarize([row('')],[{'suggested_key':''}])
        self.assertEqual(d['empty_manifest_keys'],1);self.assertEqual(d['empty_candidate_keys'],1)

if __name__ == '__main__':
    unittest.main()
