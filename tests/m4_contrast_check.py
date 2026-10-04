import re

def srgb_to_lum(hex_color):
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    r, g, b = [int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4)]
    def adj(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * adj(r) + 0.7152 * adj(g) + 0.0722 * adj(b)

def contrast(c1, c2):
    l1 = srgb_to_lum(c1)
    l2 = srgb_to_lum(c2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)

surfaces = {
    'canvas (#0c1622)': '#0c1622',
    'surface (#142130)': '#142130',
    'surface-soft (#192a3c)': '#192a3c',
}

texts = [
    ('--ink', '#e2ecf5'),
    ('--ink-soft', '#a2bed6'),
    ('--muted', '#799ab5'),
    ('--quiet', '#55748f'),
    ('--blue', '#29a0eb'),
    ('--blue-deep', '#54bcf7'),
]

print("=== WCAG 2.1 Contrast Evaluation in Dark Mode ===")
for s_name, s_hex in surfaces.items():
    print(f"\nSurface: {s_name}")
    for t_name, t_hex in texts:
        cr = contrast(s_hex, t_hex)
        rating = "PASS (AAA)" if cr >= 7.0 else "PASS (AA)" if cr >= 4.5 else "LARGE TEXT ONLY (3:1)" if cr >= 3.0 else "FAIL (<3:1)"
        print(f"  {t_name:12} ({t_hex}): {cr:5.2f}:1 -> {rating}")
