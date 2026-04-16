import os

old_rgbas = ["252, 128, 25", "252,128,25"]
new_rgba = "255, 75, 145"

old_hex = "#FC8019"
new_hex = "#FF4B91"

templates_dir = r"c:\MaidConnect\maidproject\maidapp\templates"

for root, dirs, files in os.walk(templates_dir):
    for file in files:
        if file.endswith(".html"):
            file_path = os.path.join(root, file)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            new_content = content
            for orgba in old_rgbas:
                new_content = new_content.replace(orgba, new_rgba)
            new_content = new_content.replace(old_hex, new_hex)
            
            if new_content != content:
                print(f"Updating {file}")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
