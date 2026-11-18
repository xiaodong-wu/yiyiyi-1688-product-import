# 壹移蚁 1688 链接与 PDF 产品导入技能

面向 Codex 的产品资料处理技能：支持从 CSV 逐行读取 1688 商品链接，也可直接读取产品 PDF，提取并核验文字与图片，生成英文导入 CSV、独立产品详情及白底产品图片。

## 功能

- 一份产品 PDF 对应一个产品行，支持指定 PDF 文件夹、重复文件去重、失败隔离和批次续跑。
- 保留导入模板的列名、列顺序及映射配置，提供 [12 列工作模板](assets/content_import_template.csv)，前三列填商品链接、SandBase 密钥和 ImgBB 密钥。
- 核验材质、型号、包装和规格；缺失或存在冲突的参数不自行补全。
- 逐页覆盖 PDF 的全部产品详情文字与不同图片，生成英文标题、摘要、参数、SEO 内容、完整详情 HTML 和正文 TXT，并记录内容对应表。
- 根据真实产品照片和布局参考制作封面，有同商品 1688 轮播资料时按原顺序逐张处理白底并写入 CSV；封面与组图均为正方形，详情照片与图纸可按内容采用横幅、竖版等比例，统一输出 WebP。
- 图片统一使用随技能附带的官方 Yiant PNG；同一详情板块的图片等宽等高（包含图纸），不同板块可用不同比例。
- HTML 详情主色为 `#13b2da`，配合深青文字和浅青背景。
- 详情最大宽度为 1400px，平衡图文高度；设备、材料、包装、定制案例按源资料组织模块，随容器宽度调整排列。
- 每款详情底部新增 6 条独立的产品相关英文 FAQ，依据本品源资料回答，并校验数量、完整性和底部位置。
- 白底产品图库与详情插图分开管理，详情可保留真实设备、应用环境和原始图纸。
- 可使用模板中的 ImgBB 配置上传图片；按文件 hash 复用成功记录，避免重复上传。

## 安装和使用

将仓库克隆到 Codex 的技能目录：

```bash
git clone https://github.com/xiaodong-wu/yiyiyi-1688-product-import.git \
  ~/.codex/skills/yiyiyi-1688-product-import
```

如果该目录已经存在，请先检查现有安装，避免覆盖自己的改动。

在 Codex 中提供填好的工作模板（或产品 PDF），然后输入：

```text
使用 $yiyiyi-1688-product-import 按 CSV 各行的链接和密钥处理 1688 商品，
逐款生成英文内容、封面和白底组图，并填入我提供的 CSV 模板。
未确认的尺寸先省略，单独输出产品详情。
```

默认表头：

```csv
link,SANDBASE_API_KEY,IMGBB_API_KEY,title,remark,thumb,images,pro_fields,content,seo_title1,seo_desc,file_name
```

最终 CSV 清空密钥并移除废弃场景图列，使用 UTF-8 无 BOM 和不加引号的标准字段名表头；包含逗号、引号或换行的正文按 CSV 规范转义。PDF 到产品行的对应关系单独记录在 `.mapping.json` 中；源 PDF、上传凭据和实际导入文件保存在本地运行目录。

## 运行方式

完整流程由 Codex 按 [SKILL.md](SKILL.md) 执行，包括事实核验、图片生成及视觉检查。脚本负责可重复的提取、映射、转换、上传和校验，不会仅凭提取成功就把产品标记为完成。

Python 脚本需要 `pypdf` 和 `Pillow`。CSV 合成脚本使用 Codex bundled Node.js 与 `@oai/artifact-tool`，通过 `load_workspace_dependencies` 获取运行环境。图片生成和白底处理使用内置 imagegen。

链接模式见[逐行采集、预检与续跑](references/link-batch-workflow.md)。不承诺 SandBase 查询免费。

PDF 批量提取示例：

```bash
python3 scripts/prepare_pdf_batch.py /path/product-a.pdf /path/product-b.pdf \
  --template-csv /path/product_import_template.csv \
  --run-dir /path/product-run
```

下一步按 [PDF 批处理流程](references/pdf-batch-workflow.md) 核验并生成各产品资料、合成导入表，再执行输出校验。

## 文件说明

| 路径 | 用途 |
| --- | --- |
| `SKILL.md` | 技能入口和处理规则 |
| `agents/openai.yaml` | Codex 技能显示信息 |
| `assets/` | 空白导入模板、详情模板、配色和封面布局参考 |
| `references/` | PDF 批处理、证据字段及图片工作流 |
| `scripts/` | 提取、批处理、CSV 合成、WebP 转换、上传和校验脚本 |
| `tests/` | CSV 兼容性、详情图片来源与底部六条 FAQ 校验测试 |

运行 CSV 兼容性测试：`python3 -m unittest discover -s tests -v`。

封面布局参考来源见 [图片工作流](references/image-workflow.md)。技能不自动执行网站导入或发布。

详情结尾固定为：[英文报告区](assets/material-reports.html) → 本品六条英文 FAQ。不要生成 Buying notes & precautions、付款、退换货、售后或签收条款区。保留官方报告原文、图片顺序、站内路径、alt 和 ID；独立预览可以补全站点 https://yyy.szsdzx.com。报告仅指产品组合中的绝缘纸，不属于当前 SKU 的认证。报告原件不加品牌水印、不裁剪，通过 contain 等大展示。
