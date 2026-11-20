"""wafer.space reel label ("Signature" design, concept F in planning/).

A 62 x 28.9 mm EIGP 114 product label for component reels:

* left:  a wafer whose centre die block is the Data Matrix (ECC-200, Format 06,
         all fields). The ring of whole dies around it carries the project
         "fingerprint" -- 4 solid dies picked by a hash of the project code --
         plus hatched partial dies at the wafer edge and two logo sparkles.
* right: logo + wordmark + run, the (1P) supplier part number as the hero line
         (run prefix regular, project code bold), then (P), (Q), (10D), (1T)
         and (4L) in a caption-over-value grid.

Everything is laid out in millimetres in one SVG per label. Sizes are chosen
for a 300 dpi black-only thermal printer: Data Matrix module = 6 dots (20 mil),
rules and hatching = 2 dots. No decoration enters the 2-module quiet zone.

The fingerprint hash (FNV-1a -> mulberry32 -> partial Fisher-Yates) matches
the JavaScript in planning/reel-labels.html bit for bit.
"""
from __future__ import annotations

import math
from html import escape

from . import brand, datamatrix, spec

# --------------------------------------------------------------------------- #
# geometry (mm)
# --------------------------------------------------------------------------- #
W, H = 62.0, 28.9                     # label stock
DOT = 25.4 / 300                      # one printer dot at 300 dpi
MOD = 6 * DOT                         # Data Matrix module: 6 dots = 20 mil
HAIR = 2 * DOT                        # minimum rule / hatch weight
SAFE = (1.55, 1.5, 58.9, 25.9)        # Brother DK-11209 printable area (x, y, w, h)

RUN_PREFIX_LEN = 4                    # "G803" + project code
WAFER_CX, WAFER_CY, WAFER_R = 14.25, H / 2, 12.6
X0, X1 = 29.0, 60.4                   # right-hand type column

MONO_ADVANCE = 0.6                    # em advance of the monospace face
MIN_VALUE_MM = 1.6                    # ~4.5 pt; below this, warn

FONT_LINK = ("https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;"
             "600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap")


def _f(n: float) -> str:
    s = f"{n:.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


# --------------------------------------------------------------------------- #
# deterministic fingerprint (must match planning/reel-labels.html)
# --------------------------------------------------------------------------- #
_M32 = 0xFFFFFFFF


def _imul(a: int, b: int) -> int:
    return (a * b) & _M32


def fnv1a(s: str) -> int:
    h = 0x811C9DC5
    for ch in s:
        h ^= ord(ch)
        h = _imul(h, 0x01000193)
    return h


def _mulberry32(seed: int):
    a = seed & _M32

    def nxt() -> float:
        nonlocal a
        a = (a + 0x6D2B79F5) & _M32
        t = a
        t = _imul(t ^ (t >> 15), t | 1)
        t ^= (t + _imul(t ^ (t >> 7), t | 61)) & _M32
        return ((t ^ (t >> 14)) & _M32) / 4294967296

    return nxt


def pick_k(code: str, n: int, k: int) -> set:
    """Pick k of n indices, deterministically from ``code``."""
    r = _mulberry32(fnv1a(code))
    idx = list(range(n))
    for i in range(min(k, n)):
        j = i + int(r() * (n - i))
        idx[i], idx[j] = idx[j], idx[i]
    return set(idx[:k])


def split_part_number(pn: str):
    """'G8037KQX' -> ('G803', '7KQX'). Short values are not split."""
    if len(pn) > RUN_PREFIX_LEN:
        return pn[:RUN_PREFIX_LEN], pn[RUN_PREFIX_LEN:]
    return "", pn


# --------------------------------------------------------------------------- #
# SVG primitives
# --------------------------------------------------------------------------- #
def _text(x, y, size, s, *, mono=False, weight=None, ls=None, anchor=None,
          fill="#000"):
    a = [f'x="{_f(x)}"', f'y="{_f(y)}"', f'font-size="{_f(size)}"',
         f'class="{"f-mono" if mono else "f-sans"}"']
    if weight:
        a.append(f'font-weight="{weight}"')
    if ls:
        a.append(f'letter-spacing="{ls}"')
    if anchor:
        a.append(f'text-anchor="{anchor}"')
    a.append(f'fill="{fill}"')
    return f'<text {" ".join(a)}>{escape(s)}</text>'


def _line(x1, y1, x2, y2, w=HAIR):
    return (f'<line x1="{_f(x1)}" y1="{_f(y1)}" x2="{_f(x2)}" y2="{_f(y2)}" '
            f'stroke="#000" stroke-width="{_f(w)}"/>')


def _fit(size, text, avail):
    """Shrink a monospace size so ``text`` fits ``avail`` mm."""
    if not text:
        return size
    return min(size, avail / (MONO_ADVANCE * len(text)))


def _wafer_path(cx, cy, r, nw, nd):
    yb = cy + math.sqrt(r * r - nw * nw)
    return (f"M{_f(cx + nw)} {_f(yb)} A{_f(r)} {_f(r)} 0 1 0 {_f(cx - nw)} "
            f"{_f(yb)} L{_f(cx)} {_f(yb - nd)} Z")


def _sparkle(cx, cy, r):
    t = r * 0.16
    p = lambda x, y: f"{_f(x)} {_f(y)}"  # noqa: E731
    return (f'<path d="M{p(cx, cy - r)} Q{p(cx + t, cy - t)} {p(cx + r, cy)} '
            f'Q{p(cx + t, cy + t)} {p(cx, cy + r)} Q{p(cx - t, cy + t)} '
            f'{p(cx - r, cy)} Q{p(cx - t, cy - t)} {p(cx, cy - r)} Z" fill="#000"/>')


def _logo(cx, cy, h, fill="#000"):
    bx, by, bw, bh = brand.LOGO_BOX
    k = h / bh
    w = bw * k
    return (f'<use href="#ws-logo-cut" fill="{fill}" transform="translate('
            f'{_f(cx - w / 2 - bx * k)} {_f(cy - h / 2 - by * k)}) '
            f'scale({k:.6f})"/>')


def _logo_w(h):
    return h * brand.LOGO_BOX[2] / brand.LOGO_BOX[3]


def _wordmark(x, y, size):
    return (f'<text x="{_f(x)}" y="{_f(y)}" font-size="{_f(size)}" class="f-sans" '
            f'font-weight="600" letter-spacing="-0.04" fill="#000">wafer'
            f'<tspan font-weight="400">.space</tspan></text>')


def _datamatrix(message, x, y):
    """Data Matrix as an SVG group at (x, y); returns (svg, side_mm, n)."""
    matrix = datamatrix.encode_matrix(message)   # includes 2-module quiet zone
    n = len(matrix)
    d = []
    for r, row in enumerate(matrix):
        c = 0
        while c < n:
            if row[c]:
                s = c
                while c < n and row[c]:
                    c += 1
                d.append(f"M{s} {r}h{c - s}v1h-{c - s}z")
            else:
                c += 1
    svg = (f'<g transform="translate({_f(x)} {_f(y)}) scale({MOD:.6f})">'
           f'<rect width="{n}" height="{n}" fill="#fff"/>'
           f'<path d="{"".join(d)}" fill="#000"/></g>')
    return svg, n * MOD, n


# --------------------------------------------------------------------------- #
# the wafer frame
# --------------------------------------------------------------------------- #
def _wafer_frame(uid, message, code):
    cx, cy, r = WAFER_CX, WAFER_CY, WAFER_R
    n = len(datamatrix.encode_matrix(message))
    side = n * MOD
    x0, y0 = cx - side / 2, cy - side / 2
    cells = max(1, round(n / 4.5))       # ~4.5-module die pitch, aligned to the symbol
    q = side / cells
    g = 0.27                             # street width
    ext = math.ceil((r - side / 2) / q) + 1

    full, part = [], []
    for j in range(-ext, cells + ext):
        for i in range(-ext, cells + ext):
            if 0 <= i < cells and 0 <= j < cells:
                continue
            x, y, s = x0 + i * q + g / 2, y0 + j * q + g / 2, q - g
            ds = [math.hypot(a - cx, b - cy)
                  for a, b in ((x, y), (x + s, y), (x, y + s), (x + s, y + s))]
            if all(d < r - 0.4 for d in ds):
                full.append((x, y, s))
            elif min(ds) < r - 0.2:
                part.append((x, y, s))

    sel = pick_k(code, len(full), 4)
    hatch = 7 * DOT
    out = [
        f'<defs><clipPath id="wf{uid}"><circle cx="{_f(cx)}" cy="{_f(cy)}" '
        f'r="{_f(r - 0.2)}"/></clipPath>'
        f'<pattern id="ht{uid}" patternUnits="userSpaceOnUse" width="{_f(hatch)}" '
        f'height="{_f(hatch)}" patternTransform="rotate(45)"><rect width="{_f(HAIR)}" '
        f'height="{_f(hatch)}" fill="#000"/></pattern></defs>',
        f'<g clip-path="url(#wf{uid})">',
    ]
    for x, y, s in part:
        out.append(f'<rect x="{_f(x)}" y="{_f(y)}" width="{_f(s)}" height="{_f(s)}" '
                   f'fill="url(#ht{uid})" stroke="#000" stroke-width="{_f(HAIR)}"/>')
    out.append("</g>")
    for k, (x, y, s) in enumerate(full):
        if k in sel:
            out.append(f'<rect x="{_f(x)}" y="{_f(y)}" width="{_f(s)}" '
                       f'height="{_f(s)}" fill="#000"/>')
        else:
            out.append(f'<rect x="{_f(x)}" y="{_f(y)}" width="{_f(s)}" '
                       f'height="{_f(s)}" fill="#fff" stroke="#000" '
                       f'stroke-width="{_f(HAIR)}"/>')
    out.append(f'<path d="{_wafer_path(cx, cy, r, 0.7, 0.75)}" fill="none" '
               f'stroke="#000" stroke-width="0.25" stroke-linejoin="round"/>')
    dm_svg, _, _ = _datamatrix(message, x0, y0)
    out.append(dm_svg)                   # painted last: its quiet zone stays white
    return "".join(out), n


# --------------------------------------------------------------------------- #
# one label
# --------------------------------------------------------------------------- #
ORDER = ["customer_part_number", "supplier_part_number", "quantity",
         "date_code", "lot_code", "country_of_origin"]


def _cell(x, y_cap, caption, value, avail, warnings, label_no, *, bold=False):
    size = _fit(2.25, value, avail)
    if size < MIN_VALUE_MM:
        warnings.append(f"reel {label_no}: {caption} {value!r} shrinks to "
                        f"{size / 0.3528:.1f} pt to fit; consider a shorter value")
    return (_text(x, y_cap, 1.35, caption, weight=500, ls="0.09")
            + _text(x, y_cap + 2.6, size, value, mono=True,
                    weight=800 if bold else 600))


def build_label(fields: dict, uid: int, warnings: list):
    """Return (svg, format06_message) for one reel."""
    elements = [(spec.resolved_di(k, fields), fields[k]) for k in ORDER if k in fields]
    message = datamatrix.build_format06(elements)
    di = {k: spec.resolved_di(k, fields) for k in ORDER if k in fields}

    pn = fields["supplier_part_number"]
    run, project = split_part_number(pn)
    label_no = uid + 1

    wafer, n = _wafer_frame(uid, message, project)
    if n * MOD > SAFE[3]:
        warnings.append(f"reel {label_no}: Data Matrix ({n * MOD:.1f} mm) is taller "
                        f"than the printable area; shorten the field values")
    elif n > 36:
        warnings.append(f"reel {label_no}: payload needs a {n - 4}x{n - 4} symbol; "
                        f"it will cover the wafer's die ring")

    s = [wafer, _sparkle(3.0, 3.2, 1.25), _sparkle(26.6, 25.9, 0.85)]
    lh = 4.8
    s.append(_logo(X0 + _logo_w(lh) / 2, 3.95, lh))
    s.append(_wordmark(X0 + _logo_w(lh) + 0.8, 4.95, 2.55))
    if run:
        s.append(_text(X1, 4.7, 1.25, f"RUN {run}", mono=True, weight=600,
                       ls="0.14", anchor="end"))
    s.append(_line(X0, 6.9, X1, 6.9))

    # hero: (1P) run + project, split by weight and spacing only
    s.append(_text(X0, 9.15, 1.35, f"({di['supplier_part_number']}) SUPPLIER PART NO.",
                   weight=500, ls="0.09"))
    gap = 1.0
    hero = _fit(4.5, pn, X1 - X0 - gap)
    s.append(f'<text x="{_f(X0 - 0.2)}" y="13.75" font-size="{_f(hero)}" '
             f'class="f-mono" fill="#000">'
             f'<tspan font-weight="400">{escape(run)}</tspan>'
             f'<tspan dx="{_f(gap if run else 0)}" font-weight="800">'
             f'{escape(project)}</tspan></text>')
    s.append(_line(X0, 15.6, X1, 15.6))

    def cap(key, title):
        return f"({di[key]}) {title}"

    qx = X0 + 22.6
    if "customer_part_number" in fields:
        s.append(_cell(X0, 17.85, cap("customer_part_number", "CUST. PART NO."),
                       fields["customer_part_number"], qx - X0 - 0.6, warnings, label_no))
    s.append(_cell(qx, 17.85, cap("quantity", "QTY"), fields["quantity"],
                   X1 - qx, warnings, label_no, bold=True))
    s.append(_cell(X0, 23.0, cap("date_code", "DATE"), fields["date_code"],
                   9.0, warnings, label_no))
    s.append(_cell(X0 + 9.6, 23.0, cap("lot_code", "LOT"), fields["lot_code"],
                   qx - X0 - 9.6 - 0.6, warnings, label_no))
    s.append(_cell(qx, 23.0, cap("country_of_origin", "COO"),
                   fields["country_of_origin"], X1 - qx, warnings, label_no))

    svg = (f'<svg class="reel-label" xmlns="http://www.w3.org/2000/svg" '
           f'viewBox="0 0 {_f(W)} {_f(H)}" width="{_f(W)}mm" height="{_f(H)}mm" '
           f'text-rendering="geometricPrecision">'
           f'<rect width="{_f(W)}" height="{_f(H)}" fill="#fff"/>{"".join(s)}</svg>')
    return svg, message


# --------------------------------------------------------------------------- #
# document
# --------------------------------------------------------------------------- #
_CSS = """
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: #e9e7e2; }
body { font-family: ui-sans-serif, system-ui, sans-serif; color: #17181b; }
.f-sans { font-family: 'Space Grotesk', ui-sans-serif, system-ui, sans-serif; }
.f-mono { font-family: 'JetBrains Mono', ui-monospace, Consolas, monospace; }
.sheet { padding: 24px; display: flex; flex-direction: column; align-items: center; gap: 10px; }
.reel-label { display: block; width: 62mm; height: 28.9mm; background: #fff;
  border-radius: 1.2mm; box-shadow: 0 8px 24px rgba(20,20,40,.18); }
body.zoom .reel-label { width: 186mm; height: 86.7mm; max-width: 100%; }
.meta { font: 12px/1.4 ui-monospace, Consolas, monospace; color: #666; max-width: 186mm;
  overflow-wrap: anywhere; text-align: center; }
.bar { position: sticky; top: 0; background: #17181b; color: #fff; padding: 8px 16px;
  font: 13px/1.4 ui-sans-serif, system-ui, sans-serif; display: flex; gap: 16px;
  align-items: center; z-index: 1; }
.bar label { cursor: pointer; }
@page { size: 62mm 28.9mm; margin: 0; }
@media print {
  html, body { background: #fff; }
  .bar, .meta { display: none; }
  .sheet { padding: 0; gap: 0; page-break-after: always; break-after: page; }
  .sheet:last-child { page-break-after: auto; break-after: auto; }
  .reel-label, body.zoom .reel-label { width: 62mm; height: 28.9mm;
    border-radius: 0; box-shadow: none; }
}
"""


def _readable(msg: str) -> str:
    return (msg.replace(spec.RS, "<RS>").replace(spec.GS, "<GS>")
               .replace(spec.EOT, "<EOT>"))


def render_document(labels_fields):
    """Render reels into one HTML document (one label per print page).

    Returns (html, [format06_message, ...], [warning, ...]).
    """
    warnings: list = []
    sheets, messages = [], []
    for uid, fields in enumerate(labels_fields):
        svg, message = build_label(fields, uid, warnings)
        messages.append(message)
        sheets.append(
            f'<div class="sheet">{svg}<div class="meta">reel {uid + 1} &middot; '
            f'{escape(_readable(message))}</div></div>')

    defs = (f'<svg width="0" height="0" style="position:absolute" aria-hidden="true">'
            f'<defs><path id="ws-logo-cut" fill-rule="evenodd" d="{brand.LOGO_CUT}"/>'
            f'</defs></svg>')
    title = f"wafer.space reel labels ({len(sheets)})"
    bar = ('<div class="bar"><b>wafer.space reel labels</b>'
           f'<span>{len(sheets)} label(s) &middot; 62 &times; 28.9 mm &middot; '
           'print at 100% scale</span>'
           '<label><input type="checkbox" id="z" checked> 3&times; preview</label></div>'
           '<script>const z=document.getElementById("z"),u=()=>document.body.'
           'classList.toggle("zoom",z.checked);z.addEventListener("change",u);u();'
           '</script>')
    html = (
        "<!DOCTYPE html>\n"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{escape(title)}</title>"
        f'<link rel="stylesheet" href="{FONT_LINK}">'
        f"<style>{_CSS}</style></head>"
        f'<body class="zoom">{defs}{bar}{"".join(sheets)}</body></html>'
    )
    return html, messages, warnings
