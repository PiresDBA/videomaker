content = '@echo off\nchcp 65001\nset PYTHONIOENCODING=utf-8\n"C:\\OpenMontage\\.venv\\Scripts\\python.exe" scripts\\gerar_capitulo_trilinguo.py --prompt "O campeonato de c\u00e3es mais maluco do mundo" --slug o-campeonato-de-caes-mais-maluco-do-mundo > "C:\\videomaker\\log_geracao_campeonato.log" 2>&1\n'
data = content.encode('utf-8')
with open(r'C:\videomaker\run_geracao_campeonato.bat', 'wb') as f:
    f.write(data)
print('OK', data)
