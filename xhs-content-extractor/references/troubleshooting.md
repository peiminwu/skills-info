# Troubleshooting

## 1) 报错“需重新登录小红书”

原因：页面触发登录拦截。

处理：
1. 先在本机 Safari 登录小红书。
2. 保持 Safari 登录状态后重试。

## 2) 报错“无法启动 Safari 自动化”

原因：Safari 未开启远程自动化，或系统禁用了 SafariDriver。

处理：
1. 打开 Safari 菜单 `Develop > Allow Remote Automation`。
2. 执行一次 `safaridriver --enable`（若系统提示需要）。
3. 保持 Safari 可用并重试。

## 3) OCR 速度慢

原因：PaddleOCR 首次加载模型较慢。

处理：
1. 首次运行耐心等待。
2. 后续会复用本地模型缓存，速度会提升。

## 4) 中文乱码

原因：使用了非 `utf-8-sig` 编码打开或输出。

处理：
1. 保持默认 `--encoding utf-8-sig`。
2. 用支持 UTF-8 的编辑器或记事本重新打开。
