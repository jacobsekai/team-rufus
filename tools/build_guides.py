"""Build the downloadable guide PDFs from the text files in docs/guides/.

Run from the repo root:  python3 tools/build_guides.py

Text format, one item per line:
    # Title           ## Heading        - bullet
    [ ] checkbox      ___ writing line  > small grey note
    anything else is a paragraph; a blank line adds space.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = {
    "student-checklist.txt": "content/guides/student-checklist.pdf",
    "parent-carer-guide.txt": "content/guides/parent-carer-guide.pdf",
    "educator-briefing.txt": "content/guides/educator-briefing.pdf",
    "placement-preparation-checklist.txt": "content/members/placement-preparation-checklist.pdf",
}

PAGE_W, PAGE_H, MARGIN = 595, 842, 60
FOOTER = "DRAFT - Team Rufus student prototype. Check every fact before sharing."
ORANGE = "1 0.6 0"
DARK = "0.14 0.18 0.24"
GREY = "0.4 0.4 0.4"

# Approximate Helvetica widths (per 1pt of font size) for line wrapping.
NARROW = set("ijl.,;:'!|()[] ")
WIDE = set("mwMW@%")


def text_width(text, size):
    total = 0.0
    for ch in text:
        total += 0.28 if ch in NARROW else 0.85 if ch in WIDE else 0.56
    return total * size


def wrap(text, size, width):
    lines, line = [], ""
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if line and text_width(candidate, size) > width:
            lines.append(line)
            line = word
        else:
            line = candidate
    return lines + [line] if line else lines


def pdf_string(text):
    # WinAnsi covers the UK punctuation we use (curly quotes, dashes, pound sign).
    out = []
    for byte in text.encode("cp1252", errors="replace"):
        ch = chr(byte)
        if ch in "()\\":
            out.append("\\" + ch)
        elif 32 <= byte < 127:
            out.append(ch)
        else:
            out.append(f"\\{byte:03o}")
    return "(" + "".join(out) + ")"


class Pages:
    def __init__(self):
        self.pages = []
        self.new_page()

    def new_page(self):
        self.ops = []
        self.pages.append(self.ops)
        self.y = PAGE_H - MARGIN

    def need(self, height):
        if self.y - height < MARGIN + 30:
            self.new_page()

    def text(self, x, text, font, size, colour=DARK):
        self.ops.append(f"BT /{font} {size} Tf {colour} rg {x} {self.y:.1f} Td {pdf_string(text)} Tj ET")

    def block(self, text, font="F1", size=11, indent=0, colour=DARK, gap=4):
        lines = wrap(text, size, PAGE_W - 2 * MARGIN - indent)
        for line in lines:
            self.need(size + 4)
            self.y -= size + 4
            self.text(MARGIN + indent, line, font, size, colour)
        self.y -= gap


def render(source):
    pages = Pages()
    for raw in source.splitlines():
        line = raw.rstrip()
        if not line:
            pages.y -= 6
        elif line.startswith("# "):
            pages.block(line[2:], "F2", 22, gap=4)
            pages.ops.append(f"{ORANGE} RG 3 w {MARGIN} {pages.y:.1f} m {MARGIN + 60} {pages.y:.1f} l S")
            pages.y -= 14
        elif line.startswith("## "):
            pages.need(40)
            pages.y -= 8
            pages.block(line[3:], "F2", 14, gap=2)
        elif line.startswith("- "):
            pages.need(16)
            top = pages.y
            pages.block(line[2:], indent=18, gap=2)
            pages.ops.append(f"{ORANGE} rg {MARGIN + 6} {top - 11:.1f} 4 4 re f")
        elif line.startswith("[ ] "):
            pages.need(18)
            top = pages.y
            pages.block(line[4:], indent=22, gap=4)
            pages.ops.append(f"{DARK} RG 1 w {MARGIN + 2} {top - 15:.1f} 11 11 re S")
        elif line.startswith("___"):
            pages.need(24)
            pages.y -= 22
            pages.ops.append(f"{GREY} RG 0.5 w {MARGIN} {pages.y:.1f} m {PAGE_W - MARGIN} {pages.y:.1f} l S")
        elif line.startswith("> "):
            pages.block(line[2:], size=9, colour=GREY, gap=2)
        else:
            pages.block(line)
    return pages.pages


def build_pdf(pages):
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        None,
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
    ]
    kids = []
    for number, ops in enumerate(pages, start=1):
        footer = (
            f"BT /F1 8 Tf {GREY} rg {MARGIN} 30 Td {pdf_string(FOOTER)} Tj ET "
            f"BT /F1 8 Tf {GREY} rg {PAGE_W - MARGIN - 40} 30 Td {pdf_string(f'Page {number} of {len(pages)}')} Tj ET"
        )
        stream = "\n".join(ops + [footer]).encode("latin-1")
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1") + stream + b"\nendstream")
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] "
            f"/Contents {len(objects)} 0 R /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> >>"
        )
        kids.append(f"{len(objects)} 0 R")
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(kids)} >>"

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        body = obj if isinstance(obj, bytes) else obj.encode("latin-1")
        out += f"{index} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{offset:010d} 00000 n \n" for offset in offsets).encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def main():
    for source, target in SOURCES.items():
        text = (ROOT / "docs/guides" / source).read_text(encoding="utf-8")
        (ROOT / target).write_bytes(build_pdf(render(text)))
        print(f"Built {target}")


if __name__ == "__main__":
    main()
