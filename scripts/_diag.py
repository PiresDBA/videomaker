import json
d=json.load(open(r"C:\videomaker\hyperframes-workspace\.hyperframes\artifacts\checks\b9064475-0fd7-4cb3-b87b-08f45b2a24f7.json",encoding="utf-8"))
print("lint errorCount:",d.get("lint",{}).get("errorCount"))
print("=== ERROS (severity error) em todas as secoes ===")
for sec,data in d.items():
    if isinstance(data,dict):
        for f in data.get("findings",[]):
            if f.get("severity")=="error":
                print(sec,"|",f.get("code"),"|",f.get("message"))
                print("   fix:",f.get("fixHint"))
                print("   selector:",f.get("selector"))
