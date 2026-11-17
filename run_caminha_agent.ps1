$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
& "C:\OpenMontage\.venv\Scripts\python.exe" "C:\videomaker\scripts\flow_agent_batch.py" --prompts-file "C:\videomaker\projects\a-caminha-nova-que-ninguem-quer-usar\artifacts\image_prompts_short.json" --out-dir "C:\videomaker\projects\a-caminha-nova-que-ninguem-quer-usar\assets\images\gemini\scenes" --batch-size 3 --wait 180 --pause 2 --max-attempts 3 --layout colagem --prompt-curto *> "C:\videomaker\log_caminha_final.txt"
