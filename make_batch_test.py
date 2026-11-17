import json
from pathlib import Path
src = Path(r'C:\videomaker\projects\a-caminha-nova-que-ninguem-quer-usar\artifacts\image_prompts.json')
d = json.loads(src.read_text(encoding='utf-8'))
keys = [k for k in d if not k.startswith('_')]
test = {k: d[k] for k in keys[10:13]}
out = Path(r'C:\videomaker\batch_test_prompts.json')
out.write_text(json.dumps(test, ensure_ascii=False, indent=2), encoding='utf-8')
print('keys', list(test))
