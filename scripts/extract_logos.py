import re
import json

with open(r'C:\Users\Peter Kure\.local\share\opencode\tool-output\tool_eb7b2c470001fkR0Y3WeiTIafA', 'r', encoding='utf-8') as f:
    content = f.read()

pattern = r'/teams/[^"\']+'
matches = re.findall(pattern, content)
unique = sorted(set(matches))
for m in unique:
    print(m)
