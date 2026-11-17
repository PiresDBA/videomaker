import os, re
antigo='Astronauts_floating_inside_space'
novo='Astronauts_floating_inside_space_90028a31.jpg'
for p in [
  r'C:\videomaker\projects\frida-luna-astronautas\composition.html',
  r'C:\videomaker\hyperframes-workspace\index.html',
]:
    if os.path.exists(p):
        c=open(p,encoding='utf-8').read()
        # mostra ocorrências
        occ=re.findall(r'Astronauts[^"\s<>]+', c)
        print(p, 'ocorrencias:', occ)
        # substitui qualquer variação do nome antigo pelo novo limpo
        c2=re.sub(r'Astronauts_floating_inside_space[^"\s<>]*', novo, c)
        if c2!=c:
            open(p,'w',encoding='utf-8').write(c2)
            print('  atualizado')
        else:
            print('  sem mudanca')
    else:
        print('NAO EXISTE:', p)
