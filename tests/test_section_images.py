import tempfile
import unittest
from pathlib import Path
from test_detail_assets import validator


class SectionMedia(unittest.TestCase):
    def test_cross_row_dimensions_match_including_technical_drawings(self):
        with tempfile.TemporaryDirectory() as d:
            files={k:Path(d)/(k+'.webp') for k in ('first','drawing','other')}
            for k, f in files.items():
                validator.Image.new('RGB',(48,48) if k=='first' else (48,32)).save(f)
            content='<section id="features"><div><img src="first"></div><div><figure class="yf-technical"><img src="drawing"></figure></div></section><section><img src="other"></section>'
            self.assertEqual(validator.section_size_errors(content,files),['Different image dimensions in section: features'])
            validator.Image.new('RGB',(48,48)).save(files['drawing'])
            self.assertFalse(validator.section_size_errors(content,files))
