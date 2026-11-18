import unittest
from test_detail_assets import validator

class Reports(unittest.TestCase):
    def test_fixed_reports_and_legacy_terms(self):
        original=validator.COMPANY_HTML + validator.REPORT_HTML
        faq='<section data-product-faq="true"></section>'
        self.assertEqual(validator.check_reports(original+faq),[])
        self.assertTrue(validator.check_reports(original.replace('RoHS test report','Unverified certificate',1)+faq))
        self.assertTrue(validator.check_reports(original+original+faq))
        self.assertTrue(validator.check_reports(faq+original))
        self.assertTrue(validator.check_reports('<section id="ordering"></section>'+original+faq))
        self.assertTrue(validator.check_reports(faq))

    def test_company_text_and_position(self):
        company, report = validator.COMPANY_HTML, validator.REPORT_HTML
        faq = '<section data-product-faq="true"></section>'
        for fragment in (report, company + company + report, report + company,
                         company.replace('<h2>Company Introduction</h2>', '') + report,
                         company + '<p>Gap</p>' + report, company.replace('Guangzhou', 'Shenzhen') + report):
            with self.subTest(fragment=fragment[:35]):
                self.assertTrue(any('company paragraphs' in e for e in validator.check_reports(fragment + faq)))
