"""Check that the downloadable example is a usable, credential-free Yiant input."""
import csv
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from prepare_link_batch import prepare
from xls_to_csv import convert


class ExampleWorkbook(unittest.TestCase):
    def test_published_example_converts_and_preflights_offline(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            working = root / 'input.csv'
            self.assertEqual(convert(ROOT / 'assets/example-product-import.xls', working), 3)
            with working.open(newline='', encoding='utf-8') as f:
                rows = list(csv.reader(f))
            with (ROOT / 'assets/content_import_template.csv').open(newline='', encoding='utf-8') as f:
                self.assertEqual(rows[0], next(csv.reader(f)))
            self.assertEqual(len(rows), 4)
            for row in rows[1:]:
                self.assertEqual(len(row), 12)
                self.assertEqual(row[1:], [''] * 11)
            batch = prepare(working, root / 'run')
            self.assertEqual([p['source_file'] for p in batch['products']], [r[0] for r in rows[1:]])
            self.assertEqual([p['status'] for p in batch['products']], ['blocked'] * 3)
            self.assertFalse((root / 'run').exists())
            with self.assertRaises(FileExistsError):
                convert(ROOT / 'assets/example-product-import.xls', working)
