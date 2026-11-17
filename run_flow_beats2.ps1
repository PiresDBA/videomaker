chcp 65001 | Out-Null
$env:PYTHONIOENCODING = "utf-8"
& "C:\OpenMontage\.venv\Scripts\python.exe" "C:\videomaker\scripts\flow_fetch.py" --kind image --prompts-file "C:\videomaker\projects\o-campeonato-de-caes-mais-maluco-do-mundo\artifacts\image_prompts.json" --only "gancho_da_historia_scene_c,desenvolvimento_1_scene_c,desenvolvimento_1_scene_d,desenvolvimento_2_scene_c,desenvolvimento_2_scene_d,desenvolvimento_3_scene_c,desenvolvimento_3_scene_d,desenvolvimento_4_scene_c,desenvolvimento_5_scene_c,desenvolvimento_6_scene_c,agradecimento_scene_c" --skip-confirm --wait 180
