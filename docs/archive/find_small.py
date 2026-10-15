import json
d = json.load(open('knowledge_base_inventory.json', encoding='utf-8'))
for x in sorted(d, key=lambda x: x['page_count']):
    if x['page_count'] > 0 and x['page_count'] < 5:
        print(f"{x['filename']}")
        break
