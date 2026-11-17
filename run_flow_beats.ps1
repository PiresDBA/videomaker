chcp 65001 | Out-Null
$env:PYTHONIOENCODING = "utf-8"
& "C:\OpenMontage\.venv\Scripts\python.exe" "C:\videomaker\scripts\flow_fetch.py" --kind image --prompts-file "C:\videomaker\projects\o-campeonato-de-caes-mais-maluco-do-mundo\artifacts\image_prompts.json" --only "gancho_da_historia_scene_c" --skip-confirm --wait 180
