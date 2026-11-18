import unittest
from test_detail_assets import validator

class Reports(unittest.TestCase):
    def test_fixed_reports_and_legacy_terms(self):
        original=validator.REPORT_HTML
        faq='<section data-product-faq="true"></section>'
        self.assertEqual(validator.check_reports(original+faq),[])
        self.assertTrue(validator.check_reports(original.replace('RoHS test report','Unverified certificate',1)+faq))
        self.assertTrue(validator.check_reports(original+original+faq))
        self.assertTrue(validator.check_reports(faq+original))
        self.assertTrue(validator.check_reports('<section id="ordering"></section>'+original+faq))
        self.assertTrue(validator.check_reports(faq))
