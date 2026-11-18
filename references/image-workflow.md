# 图片与提示词

布局参考 assets/cover-layout-reference.webp 来自用户指定 URL：
https://www.wire-cablemanufacturer.com/uploadfile/2026/11/13/20261113144213uKR1xe.webp

700 × 700 电线图仅提供版式：白/浅蓝底、深蓝标题、橙色规格强调、大产品近景、底部三栏规格、蓝橙收边。
不继承 ZHENGFENG WIRE/ZF、三根电线、UL3530、12AWG、150°C/200°C、600V、Tinned Copper。

## 生成前

查看参考图和实际 SKU 清晰原图，再调用内置 imagegen。外形、孔数/孔距、表面材质和文字来自真实图与核验数据。缺实际照片，不生成拟真商品封面。
默认 1:1，建议高清尺寸；品牌标识固定使用 [官方 PNG](../assets/yiant-logo.png)，图片上的品牌使用该 Yiant 原标。默认封面=图库首张=详情首图；明确需要两个版本时才分别生成。

## 提示词

替换变量，删除未核实项；保存实际提示词到该批 prompts/cover.txt。

```text
Use case: product-mockup / ads-marketing
Asset: square B2B product cover and first gallery image.
Image 1: actual product reference [file and selected SKU].
Image 2: layout inspiration only, cover-layout-reference.webp.
Create a clean white-background industrial product cover. Preserve the real product's geometry, hole count and pattern, edges, proportions, finish and material appearance from Image 1. Do not substitute the cable product in Image 2.
Use a prominent dark-blue English heading, restrained orange specification accent, large crisp product close-up and compact bottom specification row. Keep ample white space.
Exact English text: [approved short title]; [verified model]; [verified specifications and units].
Leave the brand area blank. Composite the supplied official PNG after generation, preserving its proportions and colors.
Only use supplied facts. Do not add ratings, purity, certifications, holes or dimension arrows unless verified. No Chinese text, third-party logos, watermark, lifestyle scenery or invented accessories. Do not copy product text from the layout reference.
```

## 组图

已提供同商品 API 数据时，核对 item_id，读取 main_imgs，保持原顺序并逐张登记。image-manifest.json 的产品对象保存 carousel_sources：每项含 url 和 status（used / excluded）；排除项附 reason。每张合格组图保存 carousel_index（从 1 起）、source（对应原 URL）和 source_sha256。不可凭相似图替换；完整导出后回读 images。未提供轮播资料才从 PDF 选同 SKU 白底原图。封面、每张组图都检查实际编码尺寸为正方形；详情图按真实照片、图纸及卡片语境选比例，只等比缩放、留白或从原素材分离完整照片。不要求固定数量，不用翻转同图或生成视角凑数。
白/近白允许自然柔影；灰色场景、工厂、桌面、彩色广告、中文促销图不是可直接交付白底图。
去背景、文字翻译用 imagegen；不能改变工程结构。仅格式转换/压缩使用 Pillow 脚本。
不要任意去除铭牌、型号、批号或技术标记；无法保真翻译时另选无字图。
逐项对照孔数/孔型、连接、边缘、镀层、文字数值和单位。转换 WebP 后再次查看可读性及完整性。

## 原图中的生成标识

遇到“AI 生成”“豆包AI生成”或同类标识，保留原件并在内部清单抄录可见文字。轮播原序号、源 URL 和原图 SHA-256 随组图保留，PDF 素材保留原页及所提取原图的 SHA-256。标识本身不构成排除原因。按所示型号、颜色、轮廓和开孔制作新的商品示意图，规格依据商品选项、图纸或其他已核验资料。不得把示意图当成实拍、设备或检测证明。

生成封面、组图或详情示意图时，提示词要求画面无“AI 生成”“AI-generated”、生成工具角标或水印。以最终导出的 WebP 逐张检查四角、边沿和主体，确认没有残留标识或多余线条，并核对品牌、孔型和材质。原设备照片、图纸和报告按其原件处理。来源与复核字段见[图片清单](schema-and-evidence.md)。

## 完整详情插图

白底规则适用于 `images` 产品图库，不用于排除 PDF 详情中的设备、材料、应用或定制照片。这些照片按原模块放入详情，保留真实背景与来源语境，登记到 `detail_images`。中文标题与说明重排为英文 HTML；显示原拼图的照片子区域时可用 CSS 图片视窗，保持原图像素与几何，并在覆盖记录中保存坐标。技术图纸不生成替代图、不改尺寸，未确认的单位和规格不能转写为已验证参数。

## 品牌和板块画布

官方来源：https://yyy.szsdzx.com/uploadfile/2026/07/17/20260717094048KO2D1b.png 。使用随技能附带的透明原件；只给封面和每张产品组图叠加官方 Logo，等比置于安全留白。详情复用同一张图库文件时保留现有标识。单独导出的详情图一律从加标前的源图制作，包括工厂、材料、应用、包装、技术图和同源照片的不同画布版本。报告使用原件。版式参考中的商标不进入素材；不要将品牌标识当作材质或认证证据。先选每个 section 的目标像素尺寸，包括跨排的照片与技术图；同板块同宽高、同一网格列宽。详情从原照片内部取景，先剔除供应商拼图边线和外围白边，再按板块共同的实际宽高比输出。普通照片以自然比例铺满图片区域。轮廓紧贴边缘时，优先调整整组画幅；需要扩图时只延展空背景，产品沿用原图。图纸按完整标注范围确定画幅，报告保留原件。核对四边以及白底图库内的长直线，区分装饰边和真实零件、接线或尺寸线。发布前逐节核对实际 WebP 尺寸与 1400/1000/390px 渲染边框，浮点舍入允许 1px；不以 CSS 拉伸冒充统一输出。
