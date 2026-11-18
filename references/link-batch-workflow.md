# 1688 链接批处理

1. 使用 assets/content_import_template.csv。一行一个商品；填写 link、SANDBASE_API_KEY（SandBase，而非阿里开放平台）和 IMGBB_API_KEY（需要远程图片时）。其余九列由技能生成。没有 ImgBB 密钥仍可交付本地图文预览。每行只读本行密钥；空白不继承上一行。支持标准 detail.1688.com/offer/<id>.html 商品链接及其分享参数，不接受短链或搜索页。
2. 用下列命令预检整个表；预检不联网，不写磁盘。实际采集把 --fetch 加到同一命令。只在用户要求采集且接受可能计费时发送；不根据公开免费配额自行认定免费。保持源 CSV 的顺序和两种密钥不变；不要从聊天、环境变量或浏览器抄密钥。

        python3 scripts/prepare_link_batch.py --template-csv /path/input.csv --run-dir /path/run

   实际采集通过固定的 SandBase detail-by-url 接口执行一次同步 POST，以原始中文保留事实。按 offer ID 去重，保留首次出现行的配置。批次保存 row / offer 映射、无凭据的原始商品 JSON 及 SHA-256；同批续跑读取缓存。pending 可能已经扣费，先查账户请求记录，不直接重发。已保存且证实为同一商品的响应也可以离线复用：将 outputs[0].data 对象存入新批次的 products/offer-<id>/item.json，再运行准备器生成清单，不需要密钥或额外查询。
3. 读取 item.json：核对标题、SKU、计量单位、起订量、材质。按 main_imgs 原顺序下载公开原图，逐项核对 SKU，填写 carousel_sources；打开同一响应中的公开 detail_url（若为 offer_details 脚本，用 JSON 解码，不执行脚本），提取原始插图和正文。访问这些公开图片或详情时不发送任何 API Key。若缺少可核实的来源，记录缺项，可用同款 PDF 补充；不要悄悄加调收费接口。归档图片次序、来源 URL 和哈希，详情来源可登记 source_panel、source_sha256、context 代替 PDF 页码。
4. 按图片工作流制成正方形封面及白底组图；按详情内容生成合适尺寸插图、1400px 英文详情和底部 6 条产品 FAQ。按 PDF 流程里的 product.json 结构写入同一产品目录：source_sha256 使用 item.json 哈希，verified_source_url 等于清单中的规范化 source_file，row 只含九个生成字段。确认实物、详情文字和图源后才标 ready。
5. 图片上传以源表和清单中的 template_row 调用 upload_images_to_imgbb.py，按原图哈希复用已上传结果。用 assemble_pdf_import.mjs --manifest ... --output ... 合成，再调用 validate_output.py --batch-manifest ...；两个脚本均支持 link_batch。只将 ready 产品导出；未完成行另记。最终文件保留 link 和密钥列名，两列密钥值一律留空。上传始终读取原输入表，而非交付 CSV。

详情末尾依次放置[固定英文公司简介](../assets/company-intro.html)、[英文报告区](../assets/material-reports.html)和本品六条英文 FAQ。公司简介的两段原文紧接报告区之前。不要生成 Buying notes & precautions、付款、退换货、售后或签收条款区。保留官方报告原文、图片顺序、站内路径、alt 和 ID；独立预览可以补全站点 https://yyy.szsdzx.com。报告仅指产品组合中的绝缘纸，不属于当前 SKU 的认证。报告原件不加品牌水印、不裁剪，通过 contain 等大展示。
