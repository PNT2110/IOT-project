import re

with open("frontend/src/styles.css", encoding="utf-8") as f:
    styles_content = f.read()

with open("frontend/src/experience.css", encoding="utf-8") as f:
    exp_content = f.read()

dark_match = re.search(r"@media\s*\(\s*prefers-color-scheme\s*:\s*dark\s*\)\s*\{(.*)\}\s*$", exp_content, re.DOTALL)
if dark_match:
    dark_css = dark_match.group(1)
    exp_light_css = exp_content[:dark_match.start()]
else:
    dark_css = ""
    exp_light_css = exp_content

print(f"Dark mode CSS length: {len(dark_css)} characters")

light_combined = styles_content + "\n" + exp_light_css

white_bg_patterns = re.findall(r"([^{}]+)\{([^}]*background(?:-color)?\s*:\s*(?:#fff|#ffffff|rgb\(255,\s*255,\s*255\)|white|rgba\(255,\s*255,\s*255,\s*[\d.]+\))[^}]*)\}", light_combined)

print(f"Total light rules with white background: {len(white_bg_patterns)}")

missing_overrides = []
for sel, body in white_bg_patterns:
    sel_clean = sel.strip()
    sub_selectors = [s.strip() for s in sel_clean.split(",")]
    covered = False
    for sub in sub_selectors:
        classes = re.findall(r"\.[\w-]+", sub)
        tags = re.findall(r"^[a-z]+", sub)
        tokens = classes + tags
        if any(tok in dark_css for tok in tokens):
            covered = True
            break
    if not covered:
        missing_overrides.append((sel_clean, body.strip()))

print(f"Uncovered or potentially missing dark mode overrides: {len(missing_overrides)}")
for s, b in missing_overrides[:20]:
    print(f"  Selector: {s[:60]} -> {b[:60]}")
