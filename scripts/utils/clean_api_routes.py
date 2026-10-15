import os
import glob

api_dir = r"d:\Sem 7 Project\Project\frontend\src\api"
js_files = glob.glob(os.path.join(api_dir, "*.js"))

for filepath in js_files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace the hardcoded /api/v1
    new_content = content.replace("'/api/v1/", "'/")
    
    # Also handle backticks if there are any templates
    new_content = new_content.replace("`/api/v1/", "`/")
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {os.path.basename(filepath)}")

print("Done stripping /api/v1/ from routes.")
