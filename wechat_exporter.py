#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WeChat Article Exporter · 公众号文章导出器
==========================================
把公众号文章（mp.weixin.qq.com/s/...）导出为：
  - Markdown（图片自动下载本地化）
  - 单文件 HTML（可离线阅读 / 打印为 PDF）

仅用于个人存档公开可访问的内容。请尊重作者版权，勿批量抓取与再分发。
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# Windows 控制台 UTF-8 健壮性
for _s in (sys.stdout, sys.stderr):
    try:
        if getattr(_s, "encoding", "").lower() not in ("utf-8", "utf8"):
            _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

__version__ = "1.0.0"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

WX_RE = re.compile(r"https?://mp\.weixin\.qq\.com/s\?[^\s\"']+|https?://mp\.weixin\.qq\.com/s/[^\s\"']+", re.I)


def sanitize(name, n=80):
    name = re.sub(r'[\\/:*?"<>|\r\n\t]', "_", name).strip().strip(".")
    return (name or "wechat")[:n]


def fetch_article(url: str, session: requests.Session) -> str:
    r = session.get(url, headers={"User-Agent": UA}, timeout=20)
    r.raise_for_status()
    return r.text


def parse_article(html: str, base_url: str):
    soup = BeautifulSoup(html, "html.parser")
    title = (soup.select_one("h1.rich_media_title")
             or soup.select_one(".rich_media_title")
             or soup.find("meta", property="og:title"))
    title = title.get_text(strip=True) if title and title.name != "meta" else (title["content"] if title else "")
    account = (soup.select_one("#js_name")
               or soup.select_one(".profile_nickname")
               or soup.find("meta", property="og:site_name"))
    account = account.get_text(strip=True) if account and account.name != "meta" else (account["content"] if account else "")
    date_em = soup.select_one("#publish_time") or soup.select_one(".publish_time")
    date = date_em.get_text(strip=True) if date_em else ""
    body = soup.select_one("#js_content") or soup.select_one(".rich_media_content") or soup
    return {"title": title or "未命名文章", "account": account or "",
            "date": date, "body": body, "soup": soup}


def html_to_markdown(el, base_url, session, img_dir, imgs) -> str:
    """把文章 body 转为 Markdown，图片下载到本地。"""
    out = []
    for node in el.children:
        if not getattr(node, "name", None):
            txt = str(node).strip()
            if txt:
                out.append(txt)
            continue
        name = node.name
        text = node.get_text("", strip=True)
        if name in ("h1", "h2", "h3", "h4", "h5"):
            lvl = int(name[1]) + 1
            out.append(f"\n{'#' * lvl} {text}\n")
        elif name == "p":
            t = inline(node, base_url, session, img_dir, imgs)
            if t:
                out.append(t + "\n")
        elif name in ("br",):
            out.append("\n")
        elif name == "img":
            src = node.get("src") or node.get("data-src") or ""
            if src and src.startswith("data:"):
                continue
            if not src:
                continue
            src = urljoin(base_url, src)
            local = download_img(src, session, img_dir)
            alt = node.get("alt") or node.get("data-nickname") or ""
            out.append(f"\n![{alt}]({local})\n" if local else "")
            imgs.append(src)
        elif name == "blockquote":
            inner = html_to_markdown(node, base_url, session, img_dir, imgs)
            out.append("> " + inner.replace("\n", "\n> ").strip() + "\n")
        elif name in ("ul", "ol"):
            for i, li in enumerate(node.find_all("li", recursive=False), 1):
                t = inline(li, base_url, session, img_dir, imgs)
                marker = f"{i}. " if name == "ol" else "- "
                out.append(f"{marker}{t}\n")
        elif name in ("pre", "code"):
            out.append(f"\n```\n{node.get_text()}\n```\n")
        elif name in ("table", "section", "div", "figure"):
            inner = html_to_markdown(node, base_url, session, img_dir, imgs)
            if inner.strip():
                out.append(inner + "\n")
        else:
            t = inline(node, base_url, session, img_dir, imgs)
            if t:
                out.append(t + "\n")
    return "\n".join(x for x in out if x is not None)


def inline(node, base_url="", session=None, img_dir=None, imgs=None) -> str:
    """节点行内文本（保留链接/加粗/斜体/图片）。session+img_dir 提供时图片会下载本地化。"""
    parts = []
    for c in node.children:
        if not getattr(c, "name", None):
            parts.append(str(c))
        elif c.name == "br":
            parts.append("\n")
        elif c.name == "img":
            src = c.get("data-src") or c.get("src") or ""
            if src and not src.startswith("data:"):
                src = urljoin(base_url, src)
                local = download_img(src, session, img_dir) if session is not None and img_dir is not None else ""
                if local:
                    if imgs is not None:
                        imgs.append(src)
                    parts.append(f"![{c.get('alt','')}]({local})")
                else:
                    parts.append(f"![{c.get('alt','')}]({src})")
        elif c.name == "a":
            href = c.get("href", "")
            parts.append(f"[{c.get_text(strip=True)}]({href})")
        elif c.name in ("strong", "b"):
            parts.append(f"**{c.get_text(strip=True)}**")
        elif c.name in ("em", "i"):
            parts.append(f"*{c.get_text(strip=True)}*")
        else:
            parts.append(c.get_text())
    return "".join(parts).strip()


def download_img(url: str, session: requests.Session, img_dir: Path) -> str:
    if not url.startswith("http"):
        return url
    try:
        r = session.get(url, headers={"User-Agent": UA, "Referer": "https://mp.weixin.qq.com/"}, timeout=15)
        r.raise_for_status()
        ext = (Path(urlparse(url).path).suffix or ".jpg")
        if len(ext) > 5:
            ext = ".jpg"
        name = f"{len(list(img_dir.glob('*'))) + 1:03d}{ext}"
        dest = img_dir / name
        dest.write_bytes(r.content)
        return f"imgs/{name}"
    except requests.RequestException:
        return ""


def make_html(title, md):
    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{title}</title>
<style>body{{max-width:720px;margin:0 auto;padding:24px 16px;font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;line-height:1.8;color:#222}}img{{max-width:100%}}h1{{font-size:24px}}</style></head>
<body><h1>{title}</h1><div>{md_html(md)}</div></body></html>"""


def md_html(md):
    # 极简 md->html：代码块、标题、图片、段落
    import html as _h
    lines, out, in_code = md.splitlines(), [], False
    for ln in lines:
        if ln.strip().startswith("```"):
            in_code = not in_code
            out.append(("<pre>" if in_code else "</pre>"))
            continue
        if in_code:
            out.append(_h.escape(ln)); continue
        m = re.match(r"^(#{1,5})\s+(.*)$", ln)
        if m:
            lvl = len(m.group(1)); out.append(f"<h{lvl}>{m.group(2)}</h{lvl}>")
        elif ln.strip().startswith("!["):
            mm = re.match(r"!\[.*?\]\((.*?)\)", ln)
            out.append(f'<p><img src="{mm.group(1)}"></p>' if mm else ln)
        elif ln.strip().startswith("> "):
            out.append(f"<blockquote>{ln.strip()[2:]}</blockquote>")
        elif ln.strip() in ("-", ""):
            pass
        elif ln.strip().startswith("- "):
            out.append(f"<p>{ln.strip()[2:]}</p>")
        else:
            # 行中也可能有行内图片（inline 路径产出的 ![alt](path)）
            ln = re.sub(r"!\[(.*?)\]\((.*?)\)", r'<img src="\2" alt="\1">', ln)
            out.append(f"<p>{ln}</p>")
    return "".join(out)


def extract_url(text: str) -> str:
    m = WX_RE.search(text)
    return m.group(0) if m else text.strip()


def export_one(url: str, out_dir: Path, session: requests.Session):
    print(f"  [*] 抓取: {url[:70]}")
    html = fetch_article(url, session)
    art = parse_article(html, url)

    base = sanitize(f"{art['account']}_{art['title']}")
    # 文件夹名加 8 位 URL 哈希：公众号缺账号字段/连载同名文章/重名文章不再互相覆盖；同一篇重跑仍命中原文件夹
    base = f"{base}_{hashlib.sha1(url.encode('utf-8')).hexdigest()[:8]}"
    folder = out_dir / base
    folder.mkdir(parents=True, exist_ok=True)
    img_dir = folder / "imgs"
    img_dir.mkdir(exist_ok=True)

    imgs = []
    md = html_to_markdown(art["body"], url, session, img_dir, imgs)
    header = f"# {art['title']}\n\n> **{art['account']}** · {art['date']}\n> 来源: {url}\n\n---\n\n"
    (folder / "article.md").write_text(header + md, encoding="utf-8")

    # 单文件 HTML（图片本地相对路径）
    html_out = make_html(art["title"], md)
    (folder / "article.html").write_text(html_out, encoding="utf-8")

    print(f"  [✓] 已导出 → {folder}（Markdown + HTML + {len(imgs)} 张图片）")
    return folder


def main():
    ap = argparse.ArgumentParser(description="公众号文章导出器（仅供个人存档使用）")
    ap.add_argument("input", help="公众号文章链接 / 文本 / txt 文件（每行一条）")
    ap.add_argument("-o", "--output", default="exports", help="保存目录 (默认 exports)")
    ap.add_argument("-b", "--batch", action="store_true", help="输入是 txt 文件")
    args = ap.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"Accept-Language": "zh-CN,zh;q=0.9"})

    if args.batch:
        urls = [l.strip() for l in Path(args.input).read_text(encoding="utf-8").splitlines() if l.strip()]
        for i, u in enumerate(urls, 1):
            print(f"[{i}/{len(urls)}]")
            try:
                export_one(extract_url(u), out_dir, session)
            except requests.RequestException as e:
                print(f"  [!] 失败: {e}")
            time.sleep(1)
    else:
        try:
            export_one(extract_url(args.input), out_dir, session)
        except requests.RequestException as e:
            sys.exit(f"抓取失败: {e}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\n已取消")
