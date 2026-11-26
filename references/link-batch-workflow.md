# Import from 1688 offer links

## Prepare the working table

Use the [example XLS](../assets/example-product-import.xls) or [blank CSV](../assets/content_import_template.csv). Each product row contains a `link` and its own credentials. Use a standard `https://detail.1688.com/offer/<id>.html` URL. Share parameters are accepted. Search pages and short links cannot identify an offer reliably.

For legacy XLS files, install `xlrd` and convert the product sheet once. Keep this CSV private because it retains any entered credentials. For a workbook with several visible sheets, select one with `--sheet "Sheet name"`. CSV users can skip conversion.

```bash
python3 scripts/xls_to_csv.py /path/products.xls /path/input.csv
python3 scripts/prepare_link_batch.py --template-csv /path/input.csv --run-dir /path/link-run
```

Preflight reads the table without making network calls or writing a batch. Resolve invalid links and inspect the status of each row. Missing credentials block live lookups. Blank cells do not inherit the preceding row's keys. Deduplicate by offer ID using the first occurrence and record duplicates against that row.

## Fetch and resume

Add `--fetch` to the preflight command for an authorized, potentially billable lookup. The helper sends the canonical offer URL to the SandBase `detail-by-url` endpoint and requests original-language data. It verifies the returned `item_id` and title and records a credential-free response, SHA-256 and source row. An ambiguous request is marked `pending`. Check the provider's request history before retrying.

To reuse a verified response, place the matching `outputs[0].data` object in `products/offer-<id>/item.json` in the working batch. Run the helper with the same table to reuse it. The fetch-enabled run writes the manifest and reuses valid cache entries before considering a live query. Inspect preflight for uncached rows before enabling it. Use a new batch when the input table changes.

## Review each offer

- Check the selected SKU, unit, minimum order, options and specifications against `item.json`. Read the public original `detail_url` for the full description and its pictures. If the response is a script-wrapped data assignment, decode the data without executing the script. Retrieve public source images and detail pages without API credentials.
- Inventory `main_imgs` in source order. Match each retained view to its URL, 1-based index and SHA-256. Record reasons for exclusions. Archive original images, detail panels and relevant text with the product. Follow the [image workflow](image-workflow.md).
- Use source-panel identifiers and hashes for detail imagery. Save `product.json` with the verified canonical offer URL, response hash and nine generated fields. If additional evidence is needed, report the missing material or use an explicitly supplied same-product PDF. Keep unrelated items and extra paid endpoints out of the batch.

Use the [shared export procedure](schema-and-evidence.md#export-and-validation) to upload from the original row, assemble reviewed products and validate the output.
