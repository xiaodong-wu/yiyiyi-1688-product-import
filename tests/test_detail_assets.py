"""Keep source detail illustrations separate from the white-background gallery."""
import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

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
            (self.root/path).write_bytes(b'RIFF\x00\x00\x00\x00WEBPfixture')
        self.body = f'<div><img src="{self.cover}" alt="Product cover"><img src="{self.factory}" alt="Supplier equipment"></div>'
        self.gallery = [{'path':self.cover,'role':'cover','origin':'generated_cover','source':'fixture',
                         'alt':'Product cover','visual_reviewed':True,'product_match':True}]
        self.details = [{'path':self.factory,'role':'production','origin':'source_detail','source':'fixture.pdf',
                         'source_pages':[3],'context':'Equipment shown in supplier PDF','alt':'Supplier equipment',
                         'visual_reviewed':True,'context_reviewed':True}]

    def tearDown(self): self.tmp.cleanup()

    def errors(self):
        row = dict(title='Example',remark='Example product.',thumb=self.cover,scenario_image='',
                   images=self.cover+'|Product cover',pro_fields='Material: Steel',content=self.body,
                   seo_title1='Example',seo_desc='Example product.',file_name='example',IMGBB_API_KEY='')
        p=self.root/'product.csv'
        with p.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(row));w.writeheader();w.writerow(row)
        (self.root/'details/example.fragment.html').write_text(self.body)
        (self.root/'details/example.html').write_text('<html lang="en"><head><meta name="viewport" content="width=device-width"></head><body>'+self.body.replace('src="images/','src="../images/')+'</body></html>')
        (self.root/'details/example.txt').write_text('Example product.')
        manifest=self.root/'image-manifest.json'
        manifest.write_text(json.dumps({'products':[{'file_name':'example','images':self.gallery,'detail_images':self.details}]}))
        return validator.validate(p,'local',manifest)[0]

    def test_reviewed_production_photo_is_allowed_outside_gallery(self):
        self.assertEqual(self.errors(),[])

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
