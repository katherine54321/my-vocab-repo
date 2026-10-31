import urllib.request
import json
import sys
import os

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

repo_user = "katherine54321"
repo_name = "my-vocab-repo"

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cat_path = os.path.join(base_dir, "my-vocab-repo", "categories.json")

with open(cat_path, "r", encoding="utf-8") as f:
    cat_data = json.load(f)

urls_to_purge = []
for tag in ["v5.0.0", "main"]:
    urls_to_purge.append(f"https://purge.jsdelivr.net/gh/{repo_user}/{repo_name}@{tag}/categories.json")
    for c in cat_data["categories"]:
        urls_to_purge.append(f"https://purge.jsdelivr.net/gh/{repo_user}/{repo_name}@{tag}/data/{c['id']}.json")

print(f"Purging {len(urls_to_purge)} files from jsDelivr CDN cache...")

success_count = 0
for url in urls_to_purge:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") == "finished" or data.get("id"):
                success_count += 1
                name = url.split("@")[-1]
                print(f"✓ Purged {name}")
    except Exception as e:
        name = url.split("@")[-1]
        print(f"⚠ Failed {name}: {e}")

print(f"Done! Successfully purged {success_count}/{len(urls_to_purge)} files.")
