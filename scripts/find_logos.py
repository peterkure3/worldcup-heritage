import re

with open(r'C:\Users\Peter Kure\.local\share\opencode\tool-output\tool_eb7b2c470001fkR0Y3WeiTIafA', 'r', encoding='utf-8') as f:
    c = f.read()

hrefs = re.findall(r'href=["\']([^"\']+)["\']', c)
unique = sorted(set(hrefs))
for h in unique:
    if 'team' in h.lower() or 'logo' in h.lower() or '.svg' in h or '.png' in h:
        print(h)
