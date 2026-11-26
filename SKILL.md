---
name: yiyiyi-1688-product-import
description: Build English Yiant CMS product imports from spreadsheets of 1688 offer links or from one or more supplier PDFs. Verify the selected product, produce source-based WebP images, and deliver a CSV and a separate detail page with six FAQs per product.
---

# Yiant 1688 Product Import

Use the [Yiant field specification](references/schema-and-evidence.md), [example workbook](assets/example-product-import.xls) and [blank template](assets/content_import_template.csv). Generate each product from its own source evidence. Keep raw material, private working tables and review records separate from the deliverables.

## Choose the source

- **Spreadsheet of 1688 links.** Follow the [link workflow](references/link-batch-workflow.md). Normalize an XLS input to a private CSV. Validate each offer URL, map it to its original row and reuse verified same-offer data before making an authorized SandBase query. Read each credential only from its mapped row.
- **Supplier PDFs.** Follow the [PDF workflow](references/pdf-batch-workflow.md). Process only the selected files. Use one row per distinct verified product. Specify PDF mode explicitly when the configuration sheet also contains product links. PDF extraction needs no SandBase calls.
- Use a separate working directory per batch. Preserve input order, duplicate mappings, file hashes and failure reasons. Continue independent products when one needs clarification. Mark a product `ready` only after its facts and assets have been reviewed.

## Verify the product and write the English copy

Identify the selected variant before translating. Check material, coating, dimensions, units, weight, pack size, order quantity and available options against the original specification, labels and images. For example, three unlabelled numbers do not establish thickness, width and pitch. A nickel strip may be plated steel, and a two-parallel holder designation does not establish a current rating.

Read all product sections and all distinct images, including text embedded in panels. Map each section and image to its use, consolidation or reason for exclusion in `detail-coverage.json`. Separate product photos from factory equipment and application examples. Keep supplier terms, site navigation, recommendation tiles and unrelated products out of the buyer-facing copy. Record conflicts and unresolved facts privately. Other listings can clarify terminology but cannot supply missing specifications, certifications or claims for this SKU.

Write the nine generated fields in English, including the FAQ, alt text and new image lettering. Use `Yiant` for the public brand, including visible copy, SEO and artwork. Expand the standalone Yiant brand abbreviation in source material while preserving actual supplier model codes, original evidence, URLs and CSS identifiers. Use a `yf-brand` span where the surrounding design uppercases text. Distinguish a missing fact from a negative claim.

## Build the images and detail page

1. Follow the [image workflow](references/image-workflow.md). Use real product references and the bundled layout and logo. The same square cover supplies `thumb`, the first `images` entry and the detail hero unless the user requests separate versions. Build the white-background gallery from verified product views in source order. Keep illustration and photograph provenance distinct.
2. Populate the [detail template](assets/product_detail_template.html) from the current product's full evidence. Include relevant specifications, material, features, applications, equipment, packaging and customization where supported. Move translated labels into editable HTML. Keep buyer copy free of extraction or image-processing commentary. Escape HTML values and use scoped CSS without scripts or external fonts.
3. Use the [detail styles](assets/detail-full.css) for a 1400 px maximum width, `#13b2da` accents, dark headings and a stacked section heading and introduction. Use balanced columns, natural text heights and a single column at narrow widths. Keep `.yy-full .yf-section` borderless. Size all pictures in a section to a common canvas that fits the important content, including across rows. Show equipment in `section#production` as images with descriptive alt text and no per-image captions.
4. End the page with the fixed [Company Introduction](assets/company-intro.html), then [Material Test Reports & Compliance](assets/material-reports.html), then [six product FAQs](assets/faq-section.html). Preserve the two company paragraphs and the report images, order, IDs, alt text and wording. Those reports cover insulation paper in the portfolio. Omit purchasing and after-sales terms. Write six distinct questions whose answers are supported by this specific product's evidence. Record the evidence for each answer. Keep the same questions visible at the end of all detail exports.
5. Save the fragment verbatim as `content` and `details/<slug>.fragment.html`. Save a full `lang="en"` HTML page with a viewport and correct image references, plus a plain-text copy. Keep the fixed site-relative report paths in the fragment. A standalone page may use the official site origin.

## Export and verify

Use the [shared export and validation procedure](references/schema-and-evidence.md#export-and-validation) for either input mode. Upload only when requested and a mapped ImgBB key is available. A local preview uses local WebP paths. A remote export uses verified direct URLs. Return counts for completed, duplicate and unresolved inputs, plus the export and preview locations. CMS publication is a separate action.
