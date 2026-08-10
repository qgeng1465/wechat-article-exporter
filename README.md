# 📄 公众号文章导出器 · WeChat Article Exporter

> 把微信公众号文章（`mp.weixin.qq.com/s/...`）导出为 **Markdown** 和**离线 HTML**，
> 图片自动下载本地化，方便个人存档 / 整理笔记 / 打印为 PDF。

```bash
python wechat_exporter.py "https://mp.weixin.qq.com/s/xxxxxxx"
```

## ✨ 功能特性

- ✅ **Markdown 导出**：标题 / 作者 / 图片 / 加粗 / 链接 / 引用 / 代码块完整保留
- ✅ **HTML 导出**：单文件可离线阅读，浏览器直接打印成 PDF
- ✅ **图片本地化**：正文图片自动下载到 `imgs/`，无防盗链失效问题
- ✅ **批量导出**：txt 每行一条链接，自动限速
- ✅ 支持完整链接与任意分享文本（自动提取链接）
- ✅ 仅依赖 `requests` + `beautifulsoup4`

## 📦 安装

```bash
pip install requests beautifulsoup4
```

## 🚀 使用

### 单篇导出
```bash
python wechat_exporter.py "https://mp.weixin.qq.com/s/xxxxx"
# 或直接粘贴含链接的分享文本
python wechat_exporter.py "我在微信读过这篇文章 https://mp.weixin.qq.com/s/xxxxx 推荐给你"
```

### 批量导出
```bash
# links.txt 每行一条链接
python wechat_exporter.py links.txt -b
```

## 📂 输出结构

```
exports/
└── 公众号名_标题/
    ├── article.md       (Markdown，可直接粘贴进笔记软件/Obsidian)
    ├── article.html     (单文件离线阅读)
    └── imgs/            (本地化图片)
```

## ⚠️ 免责声明

本工具**仅用于学习研究及个人合理使用**（如个人归档自己关注过的公开文章）。

- 请遵守您所在国家/地区的法律法规及微信平台条款，**尊重作者版权**。
- 请勿将本工具用于任何**商业用途**、**侵权用途**，或批量抓取、再分发他人文章。
- 使用本工具产生的任何风险与法律责任由使用者自行承担。
- 如内容侵犯了您的合法权益，请联系我们，我们将第一时间移除相关链接与内容。

## ☕ 支持作者

如果这个工具帮到了你，欢迎扫码赞赏支持，让我有动力持续更新下去～

<img src="assets/donate.png" alt="赞赏码" width="200">

## 📄 License

[MIT](./LICENSE) © 2026 qgeng1465
