# Yiant 壹移蚁 · 1688 商品导入技能

把一批 1688 商品链接或产品 PDF 转成 Yiant 网站可用的英文产品资料。每款商品交付一行导入 CSV、一套 WebP 图片，以及可独立预览的英文详情页。网站管理员可先核对详情，再将完成表导入 CMS。

[下载空白 CSV 模板](https://raw.githubusercontent.com/xiaodong-wu/yiyiyi-1688-product-import/main/assets/content_import_template.csv) · [查看技能说明](SKILL.md)

## 快速开始

在 Codex 所在机器上安装技能。首次安装可运行以下命令。

```bash
git clone https://github.com/xiaodong-wu/yiyiyi-1688-product-import.git \
  ~/.codex/skills/yiyiyi-1688-product-import
```

| 手头的资料 | 准备方式 | 在 Codex 中使用 |
| --- | --- | --- |
| 1688 商品链接 | 下载模板，每行填写一个商品链接。需要实时查询时填写该行的 SandBase 密钥，需要上传图片时再填写 ImgBB 密钥。 | 附上填好的 CSV，按链接处理。 |
| 一份或多份产品 PDF | 附上 PDF 或指定 PDF 文件夹，并提供导入模板。纯 PDF 模式可将商品链接和 SandBase 密钥留空。 | 指定按 PDF 处理，通常每份独立产品 PDF 生成一行。 |

**按链接处理**

```text
使用 $yiyiyi-1688-product-import 处理附件 CSV。先预检链接并复用已核验的同款缓存。
请告诉我还需要查询哪些商品。图片上传后，交付英文导入 CSV 和每款产品的独立详情。
```

**按 PDF 处理**

```text
使用 $yiyiyi-1688-product-import 处理附件中的全部产品 PDF，按我提供的模板填表。
从各自的 PDF 提取图片和产品资料，省略单位未确认的尺寸，先交付本地预览。
```

### 链接、密钥与费用

- `link` 填写形如 `https://detail.1688.com/offer/商品ID.html` 的详情页地址，也支持带分享参数的详情链接。同一商品 ID 在一批内去重，采用首次出现行的配置。
- `SANDBASE_API_KEY` 用于调用 SandBase 的 1688 商品详情接口。链接预检在本地完成。实时查询可能消耗赠金或产生费用，以账户账单为准。已有且核验匹配的商品响应可直接复用。
- `IMGBB_API_KEY` 用于上传该行已核对的 WebP。留空可生成本地预览。两种密钥均从对应输入行读取，最终导入表保留列名并清空值。请将填有密钥的输入表保存在本地。

## 导入表格式

模板共 12 列。前三列用于输入，后九列由技能生成。

```csv
link,SANDBASE_API_KEY,IMGBB_API_KEY,title,remark,thumb,images,pro_fields,content,seo_title1,seo_desc,file_name
```

| 字段 | 导出内容 |
| --- | --- |
| `title`、`remark` | 英文品名、已核实的型号或关键规格，以及一至两句产品摘要。 |
| `thumb`、`images` | 封面对应 `thumb`，也排在图库首位。图库每行写一个图片地址、一个竖线和英文 alt。上传版使用 ImgBB 的 WebP 直链，本地预览版使用相对路径。 |
| `pro_fields` | 首行为 `Product Name<TAB>：英文品名`，其中 `<TAB>` 代表一个实际制表符。后续每行一个属性，例如 `Material：Nickel-plated steel`。属性间使用单元格内的真实换行。 |
| `content` | 可直接放进 CMS 的英文详情 HTML 片段。 |
| `seo_title1`、`seo_desc` | 分别与 `title`、`remark` 完全一致。 |
| `file_name` | 产品文件标识，使用小写英文字母、数字和连字符。 |

最终 CSV 使用 UTF-8 无 BOM、原顺序的英文表头和标准 CSV 转义，导出时移除旧版 `scenario_image` 列。这样 CMS 可以按原名识别 `title` 等字段，并完整读取含换行的图库、参数和 HTML。

## 商品图片与英文详情

**封面和组图。** 封面按参考版式展示本品外形、型号和已核实规格，同时用作详情首图。链接模式按 1688 原始轮播顺序逐张处理，PDF 模式从本款资料选图。封面和白底组图均为正方形 WebP，使用官方 Yiant Logo。[封面布局参考](assets/cover-layout-reference.webp) · [官方 Logo](assets/yiant-logo.png)

**带“AI 生成”标识的原图。** 这类本品配图同样纳入处理。以原图和已核实规格制作新版，保留对应轮播位置。交付前逐张检查最终 WebP 的四角、边沿和主体，确认画面没有“AI 生成”字样或生成工具角标。内部图片清单保留原标识、原图来源和校验值。[图片处理规则](references/image-workflow.md)

**详情页。** 按该款 API 详情或 PDF 的完整资料组织材质、规格、设备、应用及定制等板块。正文、参数、图片说明和 FAQ 均为英文。尺寸、单位或材质有疑问时，先记录待确认项。详情专用图使用无品牌叠加的素材，同一板块的图片统一尺寸，保留技术图中的标注。工厂设备区保留英文 alt，图片下方省略逐图说明。

详情容器最大宽度为 **1400px**，主色为 `#13b2da`，板块标题和简介上下排列。页尾依次展示 **Company Introduction**、**Material Test Reports & Compliance** 和 **6 条本品专属英文 FAQ**。固定报告的适用范围为产品组合中的绝缘纸。[详情模板](assets/product_detail_template.html)

## 交付文件

| 文件 | 用途 |
| --- | --- |
| 完成表 `.csv`、同名 `.mapping.json` | 导入已核验的产品，按源链接或 PDF 追溯输出行，并查看重复或跳过项。 |
| `details/<file_name>.html` | 在浏览器中预览单个产品的完整详情。 |
| `details/<file_name>.fragment.html`、`.txt` | 分别核对与 CSV 一致的 HTML 片段和英文纯文本。 |
| `images/<file_name>/`、`image-manifest.json` | 查看最终 WebP、图片来源、轮播顺序和上传直链。 |

## 脚本与验证

在仓库根目录运行以下命令可预检链接表。预检仅读取本地输入。接受可能产生的查询费用后，可在同一命令末尾添加 `--fetch`。采集完成后，由 Codex 继续核对事实、处理图片、生成详情和组装 CSV。

```bash
python3 scripts/prepare_link_batch.py \
  --template-csv /path/input.csv --run-dir /path/product-run
```

PDF 提取使用 `pypdf` 和 `Pillow`，图片生成使用 Codex 内置 imagegen，CSV 合成使用 Codex 提供的 Node.js 和 `@oai/artifact-tool`。仓库测试可用 `python3 -m unittest discover -s tests -v` 运行。

[链接处理与缓存续跑](references/link-batch-workflow.md) · [批量 PDF 提取、合成及校验命令](references/pdf-batch-workflow.md) · [字段与来源记录](references/schema-and-evidence.md)
