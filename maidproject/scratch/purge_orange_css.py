import os

css_path = r"c:\MaidConnect\maidproject\static\css\index.css"

replacements = {
    "rgba(252, 128, 25, 0.12)": "rgba(255, 75, 145, 0.12)",
    "rgba(252,128,25,0.12)": "rgba(255, 75, 145, 0.12)",
    "rgba(252, 128, 25, 0.15)": "rgba(255, 75, 145, 0.15)",
    "rgba(252,128,25,0.15)": "rgba(255, 75, 145, 0.15)",
    "rgba(252, 128, 25, 0.2)": "rgba(255, 75, 145, 0.2)",
    "rgba(252,128,25,0.2)": "rgba(255, 75, 145, 0.2)",
    "rgba(252,128,25,0.28)": "rgba(255, 75, 145, 0.25)",
    "#FC8019": "#FF4B91",
    "background: #fff;": "background: rgba(255, 255, 255, 0.82);",
}

with open(css_path, "r", encoding="utf-8") as f:
    content = f.read()

new_content = content
for old, new in replacements.items():
    new_content = new_content.replace(old, new)

if new_content != content:
    with open(css_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("CSS updated successfully.")
else:
    print("No changes needed in CSS.")
