# Fix indentation in streamlit_app.py

with open('streamlit_app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Lines 471 to 946 need 4 more spaces of indentation
new_lines = []
for i, line in enumerate(lines):
    line_num = i + 1
    # Add 4 spaces to lines 471-946, but skip if line is except or empty
    if 471 <= line_num <= 946:
        if line.strip() and not line.strip().startswith('except'):
            new_lines.append('    ' + line)
        else:
            new_lines.append(line)
    else:
        new_lines.append(line)

with open('streamlit_app.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Fixed indentation!")
