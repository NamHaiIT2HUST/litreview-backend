import sys
with open('src/api/routes.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(782, 825):
    if lines[i].startswith('            '):
        lines[i] = lines[i][4:]

with open('src/api/routes.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
