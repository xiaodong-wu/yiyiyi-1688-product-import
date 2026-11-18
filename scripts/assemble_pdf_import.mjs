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
assert(['pdf_batch','link_batch'].includes(manifest.input_mode));
assert(['shared','positional','explicit'].includes(manifest.config_mapping), 'Resolve template mapping before exporting');
const inputBytes = await fs.readFile(manifest.template_path);
assert.equal(crypto.createHash('sha256').update(inputBytes).digest('hex'), manifest.template_sha256, 'Template changed since batch preparation');
const workbook = await Workbook.fromCSV(inputBytes.toString('utf8').replace(/^\uFEFF/,''), {sheetName:'Products'});
const sheet = workbook.worksheets.getItemAt(0);
const width = manifest.headers.length;
const inputHeaders = sheet.getRangeByIndexes(0,0,1,width).values[0];
assert.deepEqual(inputHeaders,manifest.headers);
const headers=inputHeaders.filter(h=>h!=='scenario_image');
assert(headers.every(h=>typeof h==='string' && h===h.trim() && !/[\uFEFF\u200B-\u200D\u2060\r\n]/u.test(h)), 'Header contains whitespace or invisible characters');
const sourceRows = manifest.template_rows ? sheet.getRangeByIndexes(1,0,manifest.template_rows,width).values : [];
const generated = 'title remark thumb images pro_fields content seo_title1 seo_desc file_name'.split(' ');
// Previously reviewed products used ASCII colons and sometimes called the name "Product".
function formatProductFields(text, title) {
  let name;
  const attributes = [];
  for (const line of text.split(/\r?\n/)) {
    if (!line.trim()) continue;
    const pair = /^([^:：]+)[:：](.+)$/u.exec(line);
    assert(pair && pair[1].trim() && pair[2].trim(), 'Expected an attribute name and value in pro_fields');
    const label = pair[1].trim(), value = pair[2].trim();
    if (/^product(?: name)?$/i.test(label)) {
      assert(!name || name === value, 'Conflicting product names in pro_fields');
      name = value;
    } else {
      attributes.push(label + '：' + value);
    }
  }
  return ['Product Name\t：' + (name ?? title), ...attributes].join('\n');
}
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
  assert.equal(record.source_sha256,product.source_sha256,'Product belongs to a different source');
  assert.equal(record.reviewed,true,'Product facts and images must be reviewed');
  const row = record.row;
  assert(!['IMGBB_API_KEY','SANDBASE_API_KEY'].some(key=>Object.hasOwn(row,key)),'Do not put credentials in product JSON');
  for(const h of generated) assert(typeof row[h]==='string' && row[h].trim(),`Missing generated field: ${h}`);
  row.pro_fields = formatProductFields(row.pro_fields, row.title);
  assert(/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(row.file_name),'Invalid product slug');
  assert(!slugs.has(row.file_name),'Duplicate product slugs need resolution');
  slugs.add(row.file_name);
  let sourceRow = Array(width).fill('');
  if(product.template_row != null) {
    assert(Number.isInteger(product.template_row) && product.template_row>=2 && product.template_row<=sourceRows.length+1,'Invalid template configuration row');
    sourceRow = sourceRows[product.template_row-2];
  } else assert(sourceRows.length===0,'Choose the configuration row explicitly');
  if (manifest.input_mode==='link_batch') {
    const source=await fs.readFile(safePath(product.source_data));
    assert(crypto.createHash('sha256').update(source).digest('hex')===product.source_sha256,'Cached source changed');
    const url=new URL(String(sourceRow[inputHeaders.indexOf('link')]).trim());
    const canonical='https://detail.1688.com/offer/'+JSON.parse(source).item_id+'.html';
    assert(url.hostname==='detail.1688.com' && url.pathname.replace(/\/$/,'')===new URL(canonical).pathname && canonical===product.source_file && record.verified_source_url===canonical,'Link row or reviewed offer mismatch');
  }
  const values = headers.map(h=> generated.includes(h) ? row[h] : ['SANDBASE_API_KEY','IMGBB_API_KEY'].includes(h) ? '' : h==='link' ? (record.verified_source_url || '') : (sourceRow[inputHeaders.indexOf(h)]??''));
  rows.push(values);
  mapping.push({output_row:rows.length+1,product_id:product.product_id,source_file:product.source_file,
    source_sha256:product.source_sha256,template_row:product.template_row,file_name:row.file_name});
}
assert(rows.length,'No reviewed ready products to export');
sheet.getRangeByIndexes(0,0,1,headers.length).values = [headers];
sheet.getRangeByIndexes(1,0,Math.max(sourceRows.length,rows.length),width).clear({applyTo:'contents'});
sheet.getRangeByIndexes(1,0,rows.length,headers.length).values = rows;
workbook.recalculate();
const outputValues=sheet.getRangeByIndexes(0,0,rows.length+1,headers.length).values;
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
await fs.writeFile(mappingPath,JSON.stringify({input_mode:manifest.input_mode,rows:mapping,
  skipped:manifest.products.filter(x=>x.status!=='ready').map(x=>({product_id:x.product_id,source_file:x.source_file,status:x.status,reason:x.reason||''})),
  blocked_inputs:manifest.inputs.filter(x=>x.status==='blocked'),
  duplicates:manifest.inputs.filter(x=>x.status==='duplicate')},null,2)+'\n');
console.log(`Exported ${rows.length} products with ${headers.length} original columns; source template unchanged; credentials not logged.`);
