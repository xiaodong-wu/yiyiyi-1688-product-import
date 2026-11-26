# Yiant 1688 Product Import

Turn a spreadsheet of 1688 product links or a set of supplier PDFs into an English product catalog for the Yiant CMS. Each reviewed product gets one CSV row, its own detail page and a set of WebP images. A site administrator can preview the pages before importing the CSV.

[Download the example Excel workbook (.xls)](https://raw.githubusercontent.com/xiaodong-wu/yiyiyi-1688-product-import/main/assets/example-product-import.xls) · [Download the blank CSV template](https://raw.githubusercontent.com/xiaodong-wu/yiyiyi-1688-product-import/main/assets/content_import_template.csv)

## Install

Clone the repository into your Codex skills directory. If you already have a Git installation of the skill, update that checkout with `git pull --ff-only`.

```bash
git clone https://github.com/xiaodong-wu/yiyiyi-1688-product-import.git ~/.codex/skills/yiyiyi-1688-product-import
```

## Option 1 · Import from 1688 links

1. Open the example workbook in Excel or WPS. It contains three public product links. Replace them with your own, one link per row. Keep the header row and column order.
2. Enter a `SANDBASE_API_KEY` on each row that needs a live lookup. SandBase may charge the account or deduct credits. Codex can reuse a verified response for the same offer. Enter an `IMGBB_API_KEY` for each row whose images should be uploaded. Leave it blank for a local preview.
3. Save a private copy and attach it in Codex. The skill can read the example's `.xls` format or a UTF-8 CSV. Keep the nine product-content columns empty.

```text
Use $yiyiyi-1688-product-import with the attached spreadsheet. Check the links
and report which products need a live SandBase lookup. Use verified product
photos to create the covers and galleries, then deliver the English import CSV
and a separate detail page for each product.
```

## Option 2 · Import from supplier PDFs

Attach one PDF per product, several PDFs, or a folder of selected PDFs. Supply the blank CSV template if you need to configure image uploads. Product links and SandBase keys can stay empty. The skill extracts each file's text and pictures, checks image labels and specifications, and records the source pages. Matching files are deduplicated by content. A damaged file can be held for review while the other products proceed.

```text
Use $yiyiyi-1688-product-import to process these supplier PDFs. Use the attached
CSV template. Review every product section and image, omit unconfirmed
dimensions, and deliver a local preview, an English CSV and individual detail pages.
```

## Import fields

The example and the blank template use the same 12 columns. The exported CSV preserves their order, clears both key values and uses UTF-8 without a BOM. The first line contains plain, unquoted field names. Cells containing commas, quotes or line breaks use standard CSV escaping.

```csv
link,SANDBASE_API_KEY,IMGBB_API_KEY,title,remark,thumb,images,pro_fields,content,seo_title1,seo_desc,file_name
```

| Field | Contents |
| --- | --- |
| `link` | One 1688 offer URL. Share parameters are accepted. The export uses the canonical URL when verified. |
| `SANDBASE_API_KEY`, `IMGBB_API_KEY` | Input credentials for the mapped row. Neither key appears in the delivered product content. |
| `title`, `remark` | English product name with verified identifying details, followed by a one- or two-sentence summary in `remark`. |
| `thumb`, `images` | Cover URL and ordered gallery. Each gallery line is `URL\|English alt text`. The cover is the first entry. |
| `pro_fields` | First line: `Product Name<TAB>：English name`. Use a real tab for `<TAB>`. Each additional line is one verified attribute, such as `Material：Polycarbonate`. |
| `content` | English HTML fragment for the product detail field. |
| `seo_title1`, `seo_desc` | Exact copies of `title` and `remark`, respectively. |
| `file_name` | Unique lowercase product slug with hyphens. |

## Images and detail pages

The square cover follows the supplied layout reference and shows the actual product and verified specifications. The gallery follows the order of the original 1688 carousel or uses same-product photos from the PDF. The official Yiant logo appears on covers and gallery images. Source images with a visible AI label can be used as references for newly created illustrations. The image manifest records their origin and the final artwork is checked for visible generation labels.

Detail pages use the product's own material, production, application, packaging or drawing evidence. Images within each section share dimensions. Factory equipment sections show photographs with English alt text. Detail-only images use unbranded originals. The layout fits a 1400 px content area and adapts to narrower containers. Each page ends with the Yiant company introduction, portfolio-level insulation-paper test reports and six product-specific English FAQs.

## Deliverables

| File | Use |
| --- | --- |
| Completed `.csv` and companion `.mapping.json` | Import reviewed rows and trace them to their source links or PDFs. The mapping also identifies skipped and duplicate inputs. |
| `details/<slug>.html` | Preview one product in a browser. |
| `details/<slug>.fragment.html` and `.txt` | Inspect the CMS fragment and a plain-text copy. |
| `images/<slug>/` and `image-manifest.json` | Inspect WebP assets, source records, gallery order and verified upload URLs. |

## Run the helpers

From the repository root, run a local link preflight on your filled CSV. For an Excel input, convert the selected worksheet to a private CSV first. A preflight on the published example will flag the three empty SandBase keys unless a verified cache is available. Add `--fetch` only for authorized live lookups.

```bash
python3 scripts/xls_to_csv.py /path/products.xls /path/input.csv
python3 scripts/prepare_link_batch.py --template-csv /path/input.csv --run-dir /path/link-run
```

For a PDF batch, pass the selected files or use `--pdf-dir` with the source folder.

```bash
python3 scripts/prepare_pdf_batch.py /path/product-a.pdf /path/product-b.pdf \
  --template-csv assets/content_import_template.csv --run-dir /path/pdf-run
```

Python helpers use `xlrd` for legacy Excel input, `pypdf` for PDF extraction and `Pillow` for image processing. In a Python virtual environment, install the helper dependencies with `python3 -m pip install xlrd pypdf Pillow`. CSV assembly uses Node.js with `@oai/artifact-tool`. Codex provides the image generation tool. To run the repository checks, use `python3 -m unittest discover -s tests -v`.

[Skill instructions](SKILL.md) · [Link processing](references/link-batch-workflow.md) · [PDF processing](references/pdf-batch-workflow.md) · [Image workflow](references/image-workflow.md) · [Field and evidence reference](references/schema-and-evidence.md)
