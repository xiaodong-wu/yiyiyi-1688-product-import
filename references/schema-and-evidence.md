# 字段与证据

默认工作模板为 12 列：`link,SANDBASE_API_KEY,IMGBB_API_KEY,title,remark,thumb,images,pro_fields,content,seo_title1,seo_desc,file_name`。link、两个密钥由用户填写，其余为生成字段。两种密钥仅从原始输入行使用；生成供网站导入的 CSV 只保留空的密钥列。

导出必须是 UTF-8 无 BOM；标准字段名表头不加双引号、空格或不可见字符。数据按需使用 CSV 双引号和双引号转义，保留正文、参数和图库字段中的真实换行。用普通 UTF-8 CSV 解析器读取完成表，逐项精确匹配所有列，检查每条记录列数和每个字段值。输入模板可以兼容读取 BOM，但完成表校验必须拒绝 BOM。

| 字段 | 规则 |
| --- | --- |
| link | 链接模式输入 1688 商品详情地址；导出为该产品的规范链接。纯 PDF 模式可空。 |
| SANDBASE_API_KEY | 当前行的 SandBase 密钥，只用于 SandBase 商品查询。 |
| template | 原模板只读，可空；新正文写 content。 |
| IMGBB_API_KEY | 仅用于本行图片上传；可留空以生成本地预览。 |
| title | 英文品名、准确型号和关键规格。 |
| remark | 一至两句英文概述。 |
| pro_fields | 首行为 `Product Name<TAB>：英文品名`（<TAB> 为一个实际制表符），其后每行 `English Label：English Value`。全角冒号两侧无空格。可选项按证据用空格、斜线、空格分隔。字段和数量取决于本品资料。 |
| content | 根据 PDF 全部产品详情重排的英文 HTML 片段，无脚本；区分图片语境；最后一个内容模块为本品的六条英文 FAQ。 |
| file_name | ASCII lowercase-kebab-case，无扩展名和目录。 |
| seo_title1 / seo_desc | 分别与 title / remark 完全相同。 |
| thumb | 生成封面，与 images 第一项一致。 |
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
- origin：封面为 generated_cover，常规组图为 source_white、background_edited 或 text_localized。以带生成标识的原图重新制作的组图或详情产品示意图为 source_based_illustration。
- 对带标识素材，在成图条目写入 source_ai_label（原标识文字）和 source_sha256。对应的 carousel_sources 项也写入相同的 source_ai_label。新建产品清单写入 artwork_review_version: 1。封面、组图和经过处理的详情图均在最终 WebP 目视核对后写入 generated_label_absent_reviewed: true。沿用旧批次时可读取原有清单。带标识素材的来源字段仅供内部核验。
- source：实际原图 URL 或用户资料路径；封面可追加 references 数组。
- alt：与表格一致的英文描述。
- `images[].brand_logo_sha256` 记录所用官方透明 Logo 的 SHA-256。详情专用 `detail_images` 省略此字段；核对导出实际像素后再确认审核状态。
- visual_reviewed、product_match：实际核对后才填写 true。
- white_background：非封面图确为白底后填 true。
- direct_url：可选，成功上传后的 ImgBB WebP data.url。

提供 1688 轮播时，产品级 carousel_sources 按接口顺序逐图记录，组图逐张回指其序号、源 URL 和校验值，详见 image-workflow.md。导出器必须按清单顺序将组图写进 images 字段。封面及组图校验实际 WebP 为正方形；详情插图不限制比例。

布尔声明不能代替看图，不填写假 URL 通过校验。

可选 `detail_images` 与 `images` 并列，用于内容中出现、但不进入白底图库的原始详情图。每项保留 `path`、`source`、`source_pages`、`source_sha256`、`sha256`、英文 `alt`、`context`、`visual_reviewed`、`context_reviewed`，上传后加 `direct_url`。`role` 为 `detail_photo`、`production`、`material`、`application` 或 `drawing`；`origin` 为 `source_detail`、`text_localized` 或 `background_edited`。无需虚称白底或当前 SKU；所有登记的详情图必须实际用于内容。直接复用图库图时不重复登记。

`detail-coverage.json` 对应源 PDF 的每个详情模块及图片，记录页码、原文/摘要、模块 ID、处理决定与原因；一张拼图内多张照片分别记录视窗坐标，避免只用了其中一张却声称全部覆盖。图片中的已核实参数可重排为英文 HTML；采购须知只在内部证据表登记排除，不必保留中文整图。重复、无关、冲突、未确认项明确标注处理方式。

## 待处理行

待处理和重复项记录在 batch-manifest.json 及导出生成的 `.mapping.json`，按 source_file/product_id 追踪，不因前一份失败移动后面的模板配置。未完成产品不放入“已完成”CSV。
PDF 批处理校验使用 `--batch-manifest`，核对列顺序、ready 产品数量/顺序、PDF hash 与配置值。`--original` 只用于旧的一一对应表格编辑，不适用于模板空行到多份 PDF 的扩展。

详情末尾依次放置[固定英文公司简介](../assets/company-intro.html)、[英文报告区](../assets/material-reports.html)和本品六条英文 FAQ。公司简介的两段原文紧接报告区之前。不要生成 Buying notes & precautions、付款、退换货、售后或签收条款区。保留官方报告原文、图片顺序、站内路径、alt 和 ID；独立预览可以补全站点 https://yyy.szsdzx.com。报告仅指产品组合中的绝缘纸，不属于当前 SKU 的认证。报告原件不加品牌水印、不裁剪，通过 contain 等大展示。
