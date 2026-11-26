# Product images

## Cover and branding

Inspect clear photos of the selected SKU before creating the square cover with the available image generation tool. Use the [cover reference](../assets/cover-layout-reference.webp) for its light background, dark blue headline, orange highlights, prominent product close-up and compact specification row. Only the product's own evidence supplies geometry, text and specifications. [Layout reference source](https://www.wire-cablemanufacturer.com/uploadfile/2026/11/13/20261113144213uKR1xe.webp)

Keep the brand area clear during generation. Composite the supplied transparent [Yiant logo](../assets/yiant-logo.png) at its original proportions and colors on the cover and each gallery image. A gallery image reused unchanged inside the detail retains its logo. Create a separately exported detail variant from the unbranded source. [Official logo source](https://yyy.szsdzx.com/uploadfile/2026/07/17/20260717094048KO2D1b.png)

Adapt this prompt to the verified content and save the actual prompt in the private run directory.

```text
Create a square industrial product cover from the supplied SKU photograph.
Preserve its silhouette, openings, edges, dimensions in proportion, connections
and surface finish. Use the second image only for layout. On a light background,
place a dark blue English title, a restrained orange accent and a bottom row
with these verified facts: [approved title, model and specifications].
Reserve clear space for the supplied Yiant logo. Keep the product fully visible.
Exclude generator badges, watermarks and invented accessories or ratings.
```

## White-background gallery

For an offer with verified carousel data, inventory every image in `main_imgs` in its original order. Retain the 1-based index, original URL and SHA-256. Record whether each image was used or excluded and why. Use one faithful white-background view per eligible source image. For PDF-only input, select distinct views of the actual SKU. A gallery has as many verified views as the source supports.

Use original white-background photos where available. When translating lettering or isolating a product, compare the finished view to the source for count and shape of holes, edges, contacts, finish and proportions. Retain legible model plates and technical markings. Exclude unfaithful results. Classify assembly views and factory photos as detail evidence. Keep the square cover first in both `thumb` and `images`, then the approved gallery in order.

## Source images with generation labels

Retain the original and transcribe the visible label verbatim into the private manifest, including labels in the source language. A label alone does not disqualify a relevant source. Use the item's source data to create a new illustration faithful to the verified variant. Record it as `source_based_illustration`. Keep real factory photographs, measurements, drawings and reports as original evidence. Never represent an illustration as a documentary photo or test result.

Inspect the exported WebP at all four corners, around the edges and across the subject. Check for visible generation labels, decorative lines, incorrect branding and geometry. Record the review and original label as specified in the [image manifest](schema-and-evidence.md#image-manifest).

## Detail assets and visual checks

Review every detail panel. Separate composite images into complete photos or use a documented crop window. Retain real backgrounds in facility and application images. Move translated captions and panel text into editable HTML. Use the original technical drawings and preserve all dimensions, arrows and annotations. Keep report pages uncropped and unbranded.

Choose a pixel width and height for each section before exporting. Apply that canvas to all images across every row of the section. Select a ratio that preserves complete subjects and labels. Trim supplier collage lines, scan edges and extraneous outer margins. If extra space is needed, adjust the common aspect ratio or extend only empty background. For a mixed drawing and photo section, fit the canvas to the complete drawing. Distinguish actual product edges or dimension lines from stray decoration. Images should fill their boxes at their natural aspect ratio. Compare rendered boundaries at 1400, 1000 and 390 px, allowing a pixel of rounding.

Keep originals and intermediates under `source/` or `staging/`. Export final images as WebP, normally quality 82 and method 6, preserving orientation, proportions, transparency and legibility. Use lossless encoding where fine drawing text requires it. The converter performs encoding and compression.

```bash
python3 scripts/convert_images_to_webp.py /path/staging/product \
  --output-dir /path/output/images/product-slug --quality 82 --method 6
```
