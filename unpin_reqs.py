import re

with open("requirements.txt", "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    new_line = re.sub(r'==.*', '', line.strip())
    if new_line:
        new_lines.append(new_line + "\n")

with open("requirements.txt", "w") as f:
    f.writelines(new_lines)

print("Unpinned requirements.txt successfully")
