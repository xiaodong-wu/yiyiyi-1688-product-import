"""Keep source detail illustrations separate from the white-background gallery."""
import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from test_faq import fixture

spec = importlib.util.spec_from_file_location('validator', Path(__file__).resolve().parents[1] / 'scripts/validate_output.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class DetailAssets(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root/'images/example').mkdir(parents=True)
        (self.root/'details').mkdir()
        self.cover = 'images/example/cover.webp'
        self.factory = 'images/example/factory.webp'
        for path in (self.cover, self.factory):
            validator.Image.new("RGB", (20,20) if path==self.cover else (40,20)).save(self.root/path, "WEBP")
        self.body = f'<div><img src="{self.cover}" alt="Product cover"><img src="{self.factory}" alt="Supplier equipment"></div>'
        self.gallery = [{'path':self.cover,'role':'cover','origin':'generated_cover','source':'fixture',
                         'brand_logo_sha256':validator.OFFICIAL_LOGO_HASH,
                         'alt':'Product cover','visual_reviewed':True,'product_match':True}]
        self.details = [{'path':self.factory,'role':'production','origin':'source_detail','source':'fixture.pdf',
                         'source_pages':[3],'context':'Equipment shown in supplier PDF','alt':'Supplier equipment',
                         'visual_reviewed':True,'context_reviewed':True}]

    def tearDown(self): self.tmp.cleanup()

    def errors(self):
        if 'data-product-faq' not in self.body:
            self.body += validator.COMPANY_HTML + validator.REPORT_HTML + fixture()
        row = dict(title='Example',remark='Example product.',thumb=self.cover,
                   images='\n'.join(e['path']+'|'+e['alt'] for e in self.gallery),pro_fields='Product Name\t：Example\nMaterial：Steel',content=self.body,
                   seo_title1='Example',seo_desc='Example product.',file_name='example',IMGBB_API_KEY='')
        p=self.root/'product.csv'
        with p.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(row));w.writeheader();w.writerow(row)
        (self.root/'details/example.fragment.html').write_text(self.body)
        (self.root/'details/example.html').write_text('<html lang="en"><head><meta name="viewport" content="width=device-width"></head><body>'+self.body.replace('src="images/','src="../images/')+'</body></html>')
        (self.root/'details/example.txt').write_text('Example product.')
        manifest=self.root/'image-manifest.json'
        manifest.write_text(json.dumps({'products':[{'file_name':'example','images':self.gallery,'detail_images':self.details,**getattr(self,'extra_manifest',{})}]}))
        return validator.validate(p,'local',manifest)[0]

    def test_reviewed_production_photo_is_allowed_outside_gallery(self):
        self.assertEqual(self.errors(),[])

    def test_brand_is_checked_in_visible_copy_and_alt_only(self):
        page = '<style>.yy-full {color:red}</style><div class="yy-product" title="Yiant"><img src="/YY/1" alt="Model YY-32650"></div>'
        self.assertFalse(validator.HTMLImages(page).has_legacy_brand)
        for content in ('<p>YY strip</p>', '<img alt="YY reel">', '<h2>&#89;Y</h2>', '<title>YY product</title>'):
            self.assertTrue(validator.HTMLImages(content).has_legacy_brand)
        self.body += '<h2>YY battery strip</h2>'
        self.assertTrue(any('Use Yiant' in e for e in self.errors()))

    def test_branding_is_limited_to_gallery_files(self):
        self.gallery[0].pop('brand_logo_sha256')
        self.details[0]['brand_logo_sha256'] = validator.OFFICIAL_LOGO_HASH
        errors = self.errors()
        self.assertTrue(any('official Yiant logo' in e for e in errors))
        self.assertTrue(any('unbranded source' in e for e in errors))

    def test_rectangular_cover_rejected_even_if_css_would_make_it_square(self):
        validator.Image.new("RGB", (30,20)).save(self.root/self.cover, "WEBP")
        self.assertTrue(any('must be square' in error for error in self.errors()))

    def test_carousel_source_cannot_be_left_as_a_side_attachment(self):
        self.extra_manifest = {"carousel_sources":[{"url":"https://example.test/angle.jpg","status":"used"}]}
        self.assertTrue(any("carousel source order" in e for e in self.errors()))

    def labeled_carousel(self):
        source = 'https://example.test/white-ring.jpg'
        label = '\u8c46\u5305AI\u751f\u6210'
        self.extra_manifest = {'carousel_sources': [{'url': source, 'status': 'used', 'source_ai_label': label}]}
        entry = dict(self.gallery[0], path='images/example/ring.webp', role='gallery', source=source,
                     alt='White ring illustration', origin='source_based_illustration', white_background=True,
                     source_sha256='1' * 64, carousel_index=1, source_ai_label=label,
                     generated_label_absent_reviewed=True)
        validator.Image.new('RGB', (25, 25), 'white').save(self.root/entry['path'], 'WEBP')
        self.gallery.append(entry)
        return entry

    def test_new_manifest_requires_visible_label_review_for_unmarked_cover(self):
        self.extra_manifest = {'artwork_review_version': 1}
        self.assertTrue(any('visible-label review' in error for error in self.errors()))
        self.gallery[0]['generated_label_absent_reviewed'] = True
        self.assertEqual(self.errors(), [])

    def test_labeled_source_is_eligible_in_its_original_position(self):
        self.labeled_carousel()
        self.assertEqual(self.errors(), [])

    def test_original_label_and_visual_review_are_checked(self):
        entry = self.labeled_carousel()
        entry.pop('generated_label_absent_reviewed')
        entry.pop('source_ai_label')
        errors = self.errors()
        self.assertTrue(any('visible-label review' in error for error in errors))
        self.assertTrue(any('differs between the carousel' in error for error in errors))

    def test_pdf_illustration_needs_source_hash_and_original_label(self):
        self.details[0].update(role='material', origin='source_based_illustration', source_ai_label='AI generated',
                               source_sha256='b' * 64, generated_label_absent_reviewed=True)
        self.assertEqual(self.errors(), [])
        self.details[0].pop('source_sha256')
        self.assertTrue(any('original image hash' in e for e in self.errors()))

    def test_source_illustration_cannot_be_factory_evidence(self):
        self.details[0].update(origin='source_based_illustration', source_ai_label='AI generated',
                               source_sha256='a' * 64, generated_label_absent_reviewed=True)
        self.assertTrue(any('supplied product PDF' in e for e in self.errors()))

    def test_unregistered_detail_photo_is_rejected(self):
        self.details=[]
        self.assertTrue(any('provenance' in e for e in self.errors()))

    def test_missing_context_is_rejected(self):
        del self.details[0]['context']
        self.assertTrue(any('provenance and context' in e for e in self.errors()))

    def test_unused_detail_photo_is_rejected(self):
        self.body=f'<img src="{self.cover}" alt="Product cover">'
        self.assertTrue(any('not used' in e for e in self.errors()))

    def test_generated_factory_photo_is_rejected(self):
        self.details[0]['origin']='generated_cover'
        self.assertTrue(any('supplied product PDF' in e for e in self.errors()))

    def test_incomplete_review_is_rejected(self):
        self.details[0]['context_reviewed']=False
        self.assertTrue(any('verification is incomplete' in e for e in self.errors()))


if __name__ == '__main__': unittest.main(verbosity=2)
