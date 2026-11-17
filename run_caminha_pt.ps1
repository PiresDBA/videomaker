$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
& "C:\OpenMontage\.venv\Scripts\python.exe" "C:\videomaker\scripts\gerar_capitulo_trilinguo.py" --prompt "A caminha nova que ninguém quer usar" --slug "a-caminha-nova-que-ninguem-quer-usar" --only-lang pt --wait 420 --pause 8 *> "C:\videomaker\log_caminha_pt.txt"
