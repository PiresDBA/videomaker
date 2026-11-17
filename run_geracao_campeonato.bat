@echo off
chcp 65001
set PYTHONIOENCODING=utf-8
"C:\OpenMontage\.venv\Scripts\python.exe" scripts\gerar_capitulo_trilinguo.py --prompt "O campeonato de cães mais maluco do mundo" --slug o-campeonato-de-caes-mais-maluco-do-mundo > "C:\videomaker\log_geracao_campeonato.log" 2>&1
