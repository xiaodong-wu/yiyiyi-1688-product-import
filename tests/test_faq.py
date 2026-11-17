"""FAQ quantity, pair completeness and final-position regression checks."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('validator', Path(__file__).resolve().parents[1]/'scripts/validate_output.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)

def fixture(count=6):
    return '<section data-product-faq="true">' + ''.join(
        f'<article data-faq-item="true"><h3 data-faq-question="true">Question {i}?</h3><p data-faq-answer="true">Answer {i}.</p></article>'
        for i in range(count)) + '</section>'

class FAQ(unittest.TestCase):
    def test_six_complete_pairs_at_bottom(self):
        self.assertEqual(validator.faq_errors('<div><section>Product details</section>'+fixture()+'</div>'), [])

    def test_five_or_seven_pairs_rejected(self):
        for count in (5,7):
            with self.subTest(count=count):
                self.assertTrue(any('exactly 6' in e for e in validator.faq_errors(fixture(count))))

    def test_empty_answer_rejected(self):
        self.assertTrue(any('non-empty' in e for e in validator.faq_errors(fixture().replace('Answer 2.',' '))))

    def test_duplicate_question_rejected(self):
        self.assertTrue(any('distinct' in e for e in validator.faq_errors(fixture().replace('Question 1?', 'QUESTION 0!'))))

    def test_content_after_faq_rejected(self):
        for trailing in ('<p>More content</p>', '<img src="extra.webp" alt="More">', 'More content'):
            with self.subTest(trailing=trailing):
                self.assertTrue(any('final visible' in e for e in validator.faq_errors(fixture()+trailing)))

    def test_nested_question_markup(self):
        self.assertEqual(validator.faq_errors(fixture().replace('Question 0?', '<strong>Question</strong> 0?')), [])

    def test_missing_faq_rejected(self):
        self.assertTrue(any('marked product FAQ' in e for e in validator.faq_errors('<p>Product</p>')))

if __name__ == '__main__': unittest.main(verbosity=2)
