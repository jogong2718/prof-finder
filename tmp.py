import json

bios = json.load(open('./data/bios.json', 'r'))
updated = []
for key in bios.keys():
    updated.append({'name': key, 'bio': bios[key]})

with open('./data/bios.json', 'w') as f:
    json.dump(updated, f)