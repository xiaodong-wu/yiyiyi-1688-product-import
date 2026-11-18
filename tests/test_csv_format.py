"""Regression tests for website-compatible CSV headers; fixtures contain no real credentials."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('validator', Path(__file__).resolve().parents[1] / 'scripts/validate_output.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)
HEADERS = 'link SANDBASE_API_KEY IMGBB_API_KEY title remark thumb images pro_fields content seo_title1 seo_desc file_name'.split()


class CsvFormat(unittest.TestCase):
    def check_rejected(self, raw, expected):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.csv'
            path.write_bytes(raw)
            # Encoding failures must be caught before asset/metadata validation.
            errors, _ = validator.validate(path, 'local', Path(directory) / 'not-needed.json')
            self.assertTrue(any(expected in error for error in errors), errors)

    def test_product_fields_keep_order_values_and_fullwidth_colons(self):
        legacy = 'Material: Steel / Nickel\nProduct: Roll\nRatio: 2:1\nThickness: ≥ 0.15mm'
        expected = 'Product Name\t：Roll\nMaterial：Steel / Nickel\nRatio：2:1\nThickness：≥ 0.15mm'
        self.assertEqual(validator.expected_product_fields(legacy, 'Example'), expected)
        self.assertEqual(validator.expected_product_fields(expected, 'Example'), expected)
        self.assertIsNone(validator.expected_product_fields('Material：', 'Example'))
        self.assertIsNone(validator.expected_product_fields('Product: A\nProduct Name：B', 'Example'))

    def test_bom_before_quoted_title_is_rejected(self):
        raw = ('\ufeff' + ','.join('"'+h+'"' for h in HEADERS) + '\r\n').encode()
        self.check_rejected(raw, 'BOM')

    def test_bom_before_plain_title_is_rejected(self):
        self.check_rejected(('\ufeff'+','.join(HEADERS)+'\r\n').encode(), 'BOM')

    def test_quoted_ascii_header_is_rejected(self):
        raw = (','.join('"'+h+'"' for h in HEADERS)+'\r\n').encode()
        self.check_rejected(raw, 'unquoted field names')

    def test_hidden_character_in_another_header_is_rejected(self):
        headers = list(HEADERS)
        headers[1] += '\u200b'
        self.check_rejected((','.join(headers)+'\r\n').encode(), 'invisible characters')

    def test_wrong_data_column_count_is_rejected(self):
        raw = (','.join(HEADERS)+'\r\n'+'one,two\r\n').encode()
        self.check_rejected(raw, 'field count')

    def test_duplicate_header_is_rejected(self):
        self.check_rejected((','.join(HEADERS+['remark'])+'\r\n').encode(), 'Duplicate CSV headers')

    def test_unclosed_quoted_data_is_rejected(self):
        self.check_rejected((','.join(HEADERS)+'\r\n"unfinished').encode(), 'not valid UTF-8 CSV')


if __name__ == '__main__':
    unittest.main(verbosity=2)
