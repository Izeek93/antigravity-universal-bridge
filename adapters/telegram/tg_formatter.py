import os
import sys

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import re
import html

def md_to_tg_html(text: str) -> str:
    if not text:
        return ""

    # 1. Protect existing valid Telegram HTML tags
    valid_tags = []
    def save_valid_tag(match):
        idx = len(valid_tags)
        valid_tags.append(match.group(0))
        return f"___VALID_TAG_{idx}___"

    tag_regex = re.compile(r"</?(?:b|strong|i|em|code|pre|u|s|strike|blockquote)\b[^>]*>|<a\s+href=[\"'][^\"']+[\"'][^>]*>|</a>", re.IGNORECASE)
    text = tag_regex.sub(save_valid_tag, text)

    # 2. Protect multi-line code blocks ```lang ... ```
    code_blocks = []
    def save_code_block(match):
        code = match.group(1).strip("\r\n")
        escaped_code = html.escape(code)
        idx = len(code_blocks)
        code_blocks.append(f"<pre><code>{escaped_code}</code></pre>")
        return f"___CODE_BLOCK_{idx}___"

    text = re.sub(r"```(?:\w+)?\n?(.*?)```", save_code_block, text, flags=re.DOTALL)

    # 3. Protect inline code `...`
    inline_codes = []
    def save_inline_code(match):
        code = match.group(1)
        escaped_code = html.escape(code)
        idx = len(inline_codes)
        inline_codes.append(f"<code>{escaped_code}</code>")
        return f"___INLINE_CODE_{idx}___"

    text = re.sub(r"`([^`\n]+)`", save_inline_code, text)

    # 4. Markdown links: [Title](https://...) -> <a href="https://...">Title</a>
    links = []
    def save_markdown_link(match):
        title = html.escape(match.group(1))
        url = match.group(2)
        idx = len(links)
        links.append(f'<a href="{url}">{title}</a>')
        return f"___MD_LINK_{idx}___"

    text = re.sub(r"\[([^\]]+)\]\((https?://[^\)]+)\)", save_markdown_link, text)

    # 5. Escape general text
    text = html.escape(text, quote=False)

    # 6. Headers
    text = re.sub(r"^###\s+(.+)$", r"<b><u>\1</u></b>", text, flags=re.MULTILINE)
    text = re.sub(r"^##\s+(.+)$", r"<b>\1</b>", text, flags=re.MULTILINE)
    text = re.sub(r"^#\s+(.+)$", r"<b>\1</b>", text, flags=re.MULTILINE)

    # 7. Convert bold **text** to <b>text</b>
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)

    # 8. Convert italic *text* or _text_ to <i>text</i>
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"(?<!\w)_([^_\n]+)_(?!\w)", r"<i>\1</i>", text)

    # 9. Horizontal rules --- -> ———
    text = re.sub(r"^---+$", "──────────────", text, flags=re.MULTILINE)

    # 10. Restore in reverse order
    for idx, link in enumerate(links):
        text = text.replace(f"___MD_LINK_{idx}___", link)
    for idx, code in enumerate(inline_codes):
        text = text.replace(f"___INLINE_CODE_{idx}___", code)
    for idx, block in enumerate(code_blocks):
        text = text.replace(f"___CODE_BLOCK_{idx}___", block)
    for idx, tag in enumerate(valid_tags):
        text = text.replace(f"___VALID_TAG_{idx}___", tag)

    return text

if __name__ == "__main__":
    sample = """🎉 **Antigravity Universal Bridge Formatter Test**

1. 🔐 **Безопасность:**
   • Строгий <code>.gitignore</code> и нулевая утечка секретов.
   • Ссылка на документацию: [Документация](https://github.com/example/repo).

2. 📦 **Функционал:**
   • Поддержка *курсива*, **жирного шрифта** и `инлайн-кода`.
   • Автоматическое экранирование HTML."""

    res = md_to_tg_html(sample)
    print("=== RESULT ===")
    print(res)
