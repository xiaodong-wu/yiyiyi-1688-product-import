# 字段与证据

默认字段顺序与用户 PDF 导入模板一致：`title,remark,thumb,scenario_image,images,pro_fields,content,seo_title1,seo_desc,file_name,IMGBB_API_KEY`。有实际输入表时以该表表头及顺序为准；`link` 和 `template` 是旧表可选列，不是必需输入。

导出必须是 UTF-8 无 BOM；标准字段名表头不加双引号、空格或不可见字符。数据按需使用 CSV 双引号和双引号转义，保留正文、参数和图库字段中的真实换行。用普通 UTF-8 CSV 解析器读取完成表，逐项精确匹配所有列，检查每条记录列数和每个字段值。输入模板可以兼容读取 BOM，但完成表校验必须拒绝 BOM。

| 字段 | 规则 |
| --- | --- |
| link | 可选来源记录，只填 PDF 已核实的本品 URL，否则留空；不抓取此列，不保留旧示例商品链接。 |
| template | 原模板只读，可空；新正文写 content。 |
| IMGBB_API_KEY | 可空、敏感只读输入。不进入日志、JSON、审核 XLSX、ZIP 或 Git。原 CSV 含密钥时完成版原样保留，只保存在用户原指定范围。 |
| title | 英文品名、准确型号和关键规格。 |
| remark | 一至两句英文概述。 |
| pro_fields | 通常 4–8 行，无 bullet/横线/序号；事实少时不凑数，但关键缺失应暂停。 |
| content | 根据 PDF 全部产品详情重排的英文 HTML 片段，无脚本；本品图片与有来源的设备/应用/定制案例分清语境。 |
| file_name | ASCII lowercase-kebab-case，无扩展名和目录。 |
| seo_title1 / seo_desc | 分别与 title / remark 完全相同。 |
| thumb | 生成封面，与 images 第一项一致。 |
| scenario_image | 可空，不自动造生活场景。 |
| images | 每行 `图片位置|English alt text`，首项封面，其余白底实拍或保真去背景/翻译图。 |

所有生成字段不含汉字，包括 HTML 和 alt。原始 link/template/未知输入列及内部证据可保留中文。不得把 Xinbada、Lifeworth 或 ZHENGFENG 写入新产品。

审核 XLSX 可用单产品 Field / English content 纵表，批量用一行一产品加参数明细。不要复制密钥。中文交付说明可以独立于英文产品表。

## evidence.json

每个商品记录 product_id、source_pdf、source_sha256、captured_at（带时区）、capture_method、selected_variant、source_title、facts、conflicts、missing、status；offer_id/source_url 可空。
facts 每项记录 field、original_text、english_label、english_value、source_location（PDF页码/截图/DOM区域）、verified。
status 为 ready、partial 或 blocked。缺失不是零，未知不是不支持；缺项放内部记录，不把“未找到认证”写成“无认证”。数字冲突先记录，不取更有营销价值的数字。
895110619709 只是一次测试商品，不是全部产品的固定规格。

## image-manifest.json

顶层 products 数组，每项含 file_name 和 images 数组。图片字段：

- path：相对输出表的本地 WebP 路径，如 images/example/01-cover.webp。
- role：首项 cover，其余 gallery。
- origin：封面 generated_cover；组图 source_white、background_edited 或 text_localized。
- source：实际原图 URL 或用户资料路径；封面可追加 references 数组。
- alt：与表格一致的英文描述。
- visual_reviewed、product_match：实际核对后才填写 true。
- white_background：非封面图确为白底后填 true。
- direct_url：可选，成功上传后的 ImgBB WebP data.url。

布尔声明不能代替看图，不填写假 URL 通过校验。

可选 `detail_images` 与 `images` 并列，用于内容中出现、但不进入白底图库的原始详情图。每项保留 `path`、`source`、`source_pages`、`source_sha256`、`sha256`、英文 `alt`、`context`、`visual_reviewed`、`context_reviewed`，上传后加 `direct_url`。`role` 为 `detail_photo`、`production`、`material`、`application` 或 `drawing`；`origin` 为 `source_detail`、`text_localized` 或 `background_edited`。无需虚称白底或当前 SKU；所有登记的详情图必须实际用于内容。直接复用图库图时不重复登记。

`detail-coverage.json` 对应源 PDF 的每个详情模块及图片，记录页码、原文/摘要、模块 ID、处理决定与原因；一张拼图内多张照片分别记录视窗坐标，避免只用了其中一张却声称全部覆盖。图片中的参数和采购须知可以重排为英文 HTML，不必保留中文整图。重复、无关、冲突、未确认项明确标注处理方式。

## 待处理行

待处理和重复项记录在 batch-manifest.json 及导出生成的 `.mapping.json`，按 source_file/product_id 追踪，不因前一份失败移动后面的模板配置。未完成产品不放入“已完成”CSV。
PDF 批处理校验使用 `--batch-manifest`，核对列顺序、ready 产品数量/顺序、PDF hash 与配置值。`--original` 只用于旧的一一对应表格编辑，不适用于模板空行到多份 PDF 的扩展。
