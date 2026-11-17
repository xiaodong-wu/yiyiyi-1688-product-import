# 图片与提示词

布局参考 assets/cover-layout-reference.webp 来自用户指定 URL：
https://www.wire-cablemanufacturer.com/uploadfile/2026/11/13/20261113144213uKR1xe.webp

700 × 700 电线图仅提供版式：白/浅蓝底、深蓝标题、橙色规格强调、大产品近景、底部三栏规格、蓝橙收边。
不继承 ZHENGFENG WIRE/ZF、三根电线、UL3530、12AWG、150°C/200°C、600V、Tinned Copper。

## 生成前

查看参考图和实际 SKU 清晰原图，再调用内置 imagegen。外形、孔数/孔距、表面材质和文字来自真实图与核验数据。缺实际照片，不生成拟真商品封面。
默认 1:1，建议高清尺寸；没有确认品牌就省略品牌位，不猜 Logo。默认封面=图库首张=详情首图；明确需要两个版本时才分别生成。

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
Brand: [confirmed English brand, or omit all brand marks].
Only use supplied facts. Do not add ratings, purity, certifications, holes or dimension arrows unless verified. No Chinese text, third-party logos, watermark, lifestyle scenery or invented accessories. Do not copy product text from the layout reference.
```

## 组图

选择同 SKU 白底原图，按整体、原有不同视角、细节、包装排序去重。不要求固定数量，不用翻转同图或生成视角凑数。
白/近白允许自然柔影；灰色场景、工厂、桌面、彩色广告、中文促销图不是可直接交付白底图。
去背景、文字翻译用 imagegen；不能改变工程结构。仅格式转换/压缩使用 Pillow 脚本。
不要任意去除铭牌、型号、批号或技术标记；无法保真翻译时另选无字图。
逐项对照孔数/孔型、连接、边缘、镀层、文字数值和单位。转换 WebP 后再次查看可读性及完整性。

## 完整详情插图

白底规则适用于 `images` 产品图库，不用于排除 PDF 详情中的设备、材料、应用或定制照片。这些照片按原模块放入详情，保留真实背景与来源语境，登记到 `detail_images`。中文标题与说明重排为英文 HTML；显示原拼图的照片子区域时可用 CSS 图片视窗，保持原图像素与几何，并在覆盖记录中保存坐标。技术图纸不生成替代图、不改尺寸，未确认的单位和规格不能转写为已验证参数。
