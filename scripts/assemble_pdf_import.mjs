// Copy to a writable runner directory whose node_modules points to the bundled runtime.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import { Workbook } from '@oai/artifact-tool';

const args = Object.fromEntries(process.argv.slice(2).reduce((pairs, value, i, all) => {
  if(i % 2 === 0) pairs.push([value, all[i+1]]); return pairs;
}, []));
assert(args['--manifest'] && args['--output'], 'Required: --manifest and --output');
const manifestPath = path.resolve(args['--manifest']);
const run = path.dirname(manifestPath);
const manifest = JSON.parse(await fs.readFile(manifestPath, 'utf8'));
assert.equal(manifest.input_mode, 'pdf_batch');
assert(['shared','positional','explicit'].includes(manifest.config_mapping), 'Resolve template mapping before exporting');
const inputBytes = await fs.readFile(manifest.template_path);
assert.equal(crypto.createHash('sha256').update(inputBytes).digest('hex'), manifest.template_sha256, 'Template changed since batch preparation');
const workbook = await Workbook.fromCSV(inputBytes.toString('utf8').replace(/^\uFEFF/,''), {sheetName:'Products'});
const sheet = workbook.worksheets.getItemAt(0);
const width = manifest.headers.length;
const headers = sheet.getRangeByIndexes(0,0,1,width).values[0];
assert.deepEqual(headers,manifest.headers);
assert(headers.every(h=>typeof h==='string' && h===h.trim() && !/[\uFEFF\u200B-\u200D\u2060\r\n]/u.test(h)), 'Header contains whitespace or invisible characters');
const sourceRows = manifest.template_rows ? sheet.getRangeByIndexes(1,0,manifest.template_rows,width).values : [];
const generated = 'title remark thumb scenario_image images pro_fields content seo_title1 seo_desc file_name'.split(' ');
const rows = [], mapping = [], slugs = new Set();
const safePath = value => {
  assert(value && !path.isAbsolute(value),'Product file must be relative to the batch directory');
  const resolved = path.resolve(run,value);
  assert(resolved.startsWith(run+path.sep),'Product file escapes batch directory');
  return resolved;
};
for (const product of manifest.products) {
  if (product.status !== 'ready') continue;
  const record = JSON.parse(await fs.readFile(safePath(product.product_file),'utf8'));
  assert.equal(record.source_sha256,product.source_sha256,'Product belongs to a different PDF');
  assert.equal(record.reviewed,true,'Product facts and images must be reviewed');
  const row = record.row;
  assert(!Object.hasOwn(row,'IMGBB_API_KEY'),'Do not put credentials in product JSON');
  for(const h of generated) assert(typeof row[h]==='string' && (h==='scenario_image'||row[h].trim()),`Missing generated field: ${h}`);
  assert(/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(row.file_name),'Invalid product slug');
  assert(!slugs.has(row.file_name),'Duplicate product slugs need resolution');
  slugs.add(row.file_name);
  let sourceRow = Array(width).fill('');
  if(product.template_row != null) {
    assert(Number.isInteger(product.template_row) && product.template_row>=2 && product.template_row<=sourceRows.length+1,'Invalid template configuration row');
    sourceRow = sourceRows[product.template_row-2];
  } else assert(sourceRows.length===0,'Choose the configuration row explicitly');
  const values = headers.map((h,i)=> generated.includes(h) ? row[h] : h==='link' ? (record.verified_source_url || '') : (sourceRow[i]??''));
  rows.push(values);
  mapping.push({output_row:rows.length+1,product_id:product.product_id,source_file:product.source_file,
    source_sha256:product.source_sha256,template_row:product.template_row,file_name:row.file_name});
}
assert(rows.length,'No reviewed ready products to export');
sheet.getRangeByIndexes(1,0,Math.max(sourceRows.length,rows.length),width).clear({applyTo:'contents'});
sheet.getRangeByIndexes(1,0,rows.length,width).values = rows;
workbook.recalculate();
const outputValues=sheet.getRangeByIndexes(0,0,rows.length+1,width).values;
assert(JSON.stringify(outputValues)===JSON.stringify([headers,...rows]),'Spreadsheet values did not round-trip; output stopped');
// Match the website template: plain UTF-8 without BOM and quote only CSV-special values.
const quote = value => {
  const text = String(value??'');
  return /[",\r\n]/.test(text) ? '"'+text.replaceAll('"','""')+'"' : text;
};
const output = path.resolve(args['--output']);
assert(output!==path.resolve(manifest.template_path),'Never overwrite the source template');
await fs.mkdir(path.dirname(output),{recursive:true});
// Exclusive create prevents accidental overwrite of an earlier batch; use a new output name for revisions.
await fs.writeFile(output,outputValues.map(r=>r.map(quote).join(',')).join('\r\n')+'\r\n',{flag:'wx',mode:0o600});
const mappingPath = output.replace(/\.csv$/i,'')+'.mapping.json';
await fs.writeFile(mappingPath,JSON.stringify({input_mode:'pdf_batch',rows:mapping,
  skipped:manifest.products.filter(x=>x.status!=='ready').map(x=>({product_id:x.product_id,source_file:x.source_file,status:x.status,reason:x.reason||''})),
  duplicates:manifest.inputs.filter(x=>x.status==='duplicate')},null,2)+'\n');
console.log(`Exported ${rows.length} products with ${headers.length} original columns; source template unchanged; credentials not logged.`);
