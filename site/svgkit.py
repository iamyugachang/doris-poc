"""Shared inline-SVG helpers for the site diagrams (doris.apache.org palette; same look on every page)."""
import html

FONT_N = 'font-family="Inter,Noto Sans TC,sans-serif" font-size="12" font-weight="600" fill="#0f1a14"'
FONT_S = 'font-family="JetBrains Mono,monospace" font-size="9" fill="#4f5e56"'
FONT_L = 'font-family="JetBrains Mono,monospace" font-size="8" fill="#4f5e56" letter-spacing="0.06em"'
INK, MUTED, RULE, GREEN, TINT, WHITE = "#0f1a14", "#4f5e56", "#d9eee8", "#11a679", "rgba(17,166,121,.10)", "#fff"

def box(x, y, w, h, name, sub="", focal=False, dashed=False, tag=""):
    fill = TINT if focal else WHITE; stroke = GREEN if focal else (RULE if dashed else INK)
    dash = ' stroke-dasharray="4,3"' if dashed else ""
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{WHITE}"/><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="{1.2 if focal else 1}"{dash}/>'
    if tag: s += f'<rect x="{x+8}" y="{y+6}" width="{8+len(tag)*6}" height="12" rx="2" fill="transparent" stroke="rgba(15,26,20,.3)" stroke-width="0.8"/><text x="{x+12+len(tag)*3}" y="{y+15}" {FONT_L} text-anchor="middle">{tag}</text>'
    cy = y + h/2 + (2 if not sub else -4)
    s += f'<text x="{x+w/2}" y="{cy+2}" {FONT_N} text-anchor="middle">{html.escape(name)}</text>'
    if sub: s += f'<text x="{x+w/2}" y="{cy+16}" {FONT_S} text-anchor="middle">{html.escape(sub)}</text>'
    return s

def label(x, y, text, color=MUTED):
    w = 8 + len(text) * 5.4
    return f'<rect x="{x-w/2}" y="{y-9}" width="{w}" height="12" rx="2" fill="{WHITE}"/><text x="{x}" y="{y}" {FONT_L.replace('fill="#4f5e56"', f'fill="{color}"')} text-anchor="middle">{html.escape(text)}</text>'

def arrow(d, dashed=False, color=MUTED, marker="arrow"):
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.2"{" stroke-dasharray=\"4,3\"" if dashed else ""} marker-end="url(#{marker})"/>'

DEFS = f'<defs><marker id="arrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="{MUTED}"/></marker><marker id="arrow-g" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="{GREEN}"/></marker></defs>'
