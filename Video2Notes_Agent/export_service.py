import html
import io
import re
import zipfile


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", (value or "notes").strip()).strip("-").lower()
    return cleaned or "notes"


def _apply_inline_formatting(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', text)
    return text


def markdown_to_html(markdown: str) -> str:
    lines = (markdown or "").splitlines()
    html_lines = []
    in_list = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            continue

        if stripped.startswith("# "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h1>{_apply_inline_formatting(stripped[2:])}</h1>")
        elif stripped.startswith("## "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h2>{_apply_inline_formatting(stripped[3:])}</h2>")
        elif stripped.startswith("### "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h3>{_apply_inline_formatting(stripped[4:])}</h3>")
        elif stripped.startswith(("- ", "* ")):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{_apply_inline_formatting(stripped[2:])}</li>")
        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<p>{_apply_inline_formatting(stripped)}</p>")

    if in_list:
        html_lines.append("</ul>")

    return "\n".join(html_lines)


def build_export_markdown(title: str, description: str, notes: str, study_assets: dict, template: str, variant: str) -> str:
    header = [f"# {title or 'Notes'}"]
    if description:
        header.append(description)
    if template == "academic":
        header.append("_Prepared study notes_")

    body = notes or ""
    if variant == "markdown_obsidian":
        frontmatter = ["---", f'title: "{title or "Notes"}"', "source: Video2Notes", "---", ""]
        return "\n".join(frontmatter + header + ["", body])

    if variant == "markdown_notion":
        return "\n\n".join(header + [body])

    assets_lines = []
    if study_assets:
        glossary = study_assets.get("glossary") or []
        if glossary:
            assets_lines.append("## Glossary")
            for item in glossary:
                assets_lines.append(f"- **{item.get('term', 'Term')}** - {item.get('definition', '')}")
    return "\n\n".join(header + [body, "\n".join(assets_lines)]).strip()


def build_export_html(title: str, description: str, notes: str, study_assets: dict, template: str) -> str:
    assets = []
    glossary = (study_assets or {}).get("glossary") or []
    if glossary:
        assets.append("<h2>Glossary</h2>")
        assets.append("<ul>")
        for item in glossary:
            assets.append(
                f"<li><strong>{html.escape(item.get('term', 'Term'))}</strong>: {html.escape(item.get('definition', ''))}</li>"
            )
        assets.append("</ul>")

    wrapper_class = "academic" if template == "academic" else "default"
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(title or "Notes")}</title>
  <style>
    body {{ font-family: 'Segoe UI', sans-serif; margin: 0; background: #f8fafc; color: #0f172a; }}
    .sheet {{ max-width: 920px; margin: 0 auto; background: white; padding: 40px; min-height: 100vh; }}
    .sheet.academic h1, .sheet.academic h2 {{ font-family: Georgia, serif; }}
    h1, h2, h3 {{ line-height: 1.2; }}
    p, li {{ line-height: 1.7; }}
    code {{ background: #eef2ff; padding: 2px 6px; border-radius: 6px; }}
    blockquote {{ border-left: 4px solid #0f766e; padding-left: 12px; color: #334155; }}
    a {{ color: #0f766e; }}
  </style>
</head>
<body>
  <main class="sheet {wrapper_class}">
    <h1>{html.escape(title or "Notes")}</h1>
    {f"<p>{html.escape(description)}</p>" if description else ""}
    {markdown_to_html(notes)}
    {''.join(assets)}
  </main>
</body>
</html>"""


def build_docx_bytes(title: str, description: str, notes: str, study_assets: dict, template: str) -> bytes:
    body_lines = [title or "Notes"]
    if description:
        body_lines.extend(["", description])
    if template == "academic":
        body_lines.extend(["", "Prepared study notes"])
    body_lines.extend(["", re.sub(r"\[(.+?)\]\((.+?)\)", r"\1 (\2)", notes or "")])
    glossary = (study_assets or {}).get("glossary") or []
    if glossary:
        body_lines.extend(["", "Glossary"])
        for item in glossary:
            body_lines.append(f"{item.get('term', 'Term')}: {item.get('definition', '')}")

    paragraphs = []
    for line in body_lines:
        if not line:
            paragraphs.append("<w:p/>")
            continue
        paragraphs.append(
            "<w:p><w:r><w:t xml:space=\"preserve\">"
            + html.escape(line)
            + "</w:t></w:r></w:p>"
        )

    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {''.join(paragraphs)}
    <w:sectPr>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="708" w:footer="708" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>"""

    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("word/document.xml", document_xml)
    return buffer.getvalue()


def export_payload(title: str, description: str, notes: str, study_assets: dict, export_format: str, template: str) -> tuple[bytes | str, str, str]:
    safe_name = _slugify(title)
    if export_format in {"markdown_notion", "markdown_obsidian"}:
        content = build_export_markdown(title, description, notes, study_assets, template, export_format)
        return content, "text/markdown; charset=utf-8", f"{safe_name}.md"
    if export_format == "html":
        content = build_export_html(title, description, notes, study_assets, template)
        return content, "text/html; charset=utf-8", f"{safe_name}.html"
    if export_format == "docx":
        content = build_docx_bytes(title, description, notes, study_assets, template)
        return (
            content,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            f"{safe_name}.docx",
        )
    if export_format == "pdf":
        content = build_export_html(title, description, notes, study_assets, template)
        return content, "text/html; charset=utf-8", f"{safe_name}.print.html"

    content = build_export_markdown(title, description, notes, study_assets, template, "markdown_notion")
    return content, "text/markdown; charset=utf-8", f"{safe_name}.md"
