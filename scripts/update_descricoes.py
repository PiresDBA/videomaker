import subprocess
import sys

videos = [
    {
        "video_id": "hV2q4x0EMHc",
        "title": "Frida e Luna Descobrem o Espelho - Desenho Animado Infantil",
        "description": "Prepare-se para risadas com Frida e Luna, duas cachorrinhos curiosos que encontraram um espelho e não acreditam no que veem! Será que aquela outra cachorra é uma nova amiga ou uma rival estranha? Confira as reações hilárias enquanto elas latem para o próprio reflexo, fazem caretas e tentam entender esse mistério canino! Diversão garantida para toda a família em português do Brasil.",
        "tags": "frida,luna,cachorro,cachorrinha,espelho,reflexo,animacao,infantil,criancas,familia,desenho animado,cachorro engraçado,desenho,cão,pet"
    },
    {
        "video_id": "pDQl2qrFZUM",
        "title": "Luna e Frida Descobrem o Espelho da Casa - Desenho Animado",
        "description": "Luna e Frida estão de volta e dessa vez encontraram o espelho da casa! As duas amiguinhas de quatro patas ficam completamente confusas ao ver suas próprias imagens olhando de volta. Quem é essa cachorra bonita? Por que ela imita tudo que fazem? Venha rir desse momento adorável e cheio de personalidade, com narração em português do Brasil e zero texto na tela.",
        "tags": "luna,frida,cachorro,cachorrinha,espelho,reflexo,animacao,infantil,criancas,familia,desenho animado,cão engraçado,pet,cachorro fofo"
    },
    {
        "video_id": "FUcWKIM2PYQ",
        "title": "Por Que o Cachorro Gira Antes de Deitar? - Educativo Divertido",
        "description": "Você já se perguntou por que seu cachorro gira em círculos antes de deitar? Neste vídeo educativo e divertido, descobrimos esse mistério canino de forma leve e engraçada. Instintos antigos, rituais selvagens e muita fofura explicados para crianças e adultos. Tudo em português do Brasil, sem texto na tela, apenas narração e imagens adoráveis.",
        "tags": "cachorro,deitar,girar,círculos,instinto,canino,educativo,infantil,criancas,familia,curiosidade,cão,pet,comportamento animal"
    },
    {
        "video_id": "ZBnPARaNtCs",
        "title": "Limpeza dos Dentes do Cachorro - Dicas Divertidas",
        "description": "Escovar os dentes do cachorro parece missão impossível? Neste vídeo, mostramos como fazer a higiene bucal do seu pet sem estresse (ou quase). Dicas práticas, cachorrinhos cooperativos (ou não) e muita diversão para garantir um hálito fresquinho e dentes saudáveis. Em português do Brasil, para toda a família aprender enquanto se diverte.",
        "tags": "cachorro,dentes,escovação,higiene,bucal,pet,dicas,animais,infantil,família,cão,escova,dente,hálito,fresco"
    },
    {
        "video_id": "qzIt_qzlQP4",
        "title": "O Banho do Cachorro - Educativo e Divertido",
        "description": "Hora do banho! Mas será que o cachorro concorda com isso? Neste vídeo educativo e cheio de humor, acompanhamos a aventura do banho canino, desde a fuga pelo corredor até o secador de cabelo. Aprenda a dar banho no seu pet com paciência e carinho, tudo narrado em português do Brasil, sem texto na tela, só imagens e risadas.",
        "tags": "cachorro,banho,higiene,pet,dicas,animais,infantil,família,cão,secador,toalha,sabonete,banho canino"
    },
    {
        "video_id": "MywssH0c5xs",
        "title": "O Buldogue Inglês - Desenho Animado Infantil",
        "description": "Conheça o buldogue inglês mais charmoso da internet! Com aquele rostinho achatado, expressão séria e coração enorme, esse cachorro conquista a todos. Neste desenho animado divertido, veja suas trapalhadas diárias, cochilos intermináveis e amor incondicional. Narração em português do Brasil, feito para crianças e adultos que amam cães.",
        "tags": "buldogue inglês,cachorro,cão,desenho animado,infantil,criancas,família,animacao,pet,trapalhadas,cochilo,amor,cachorro engraçado"
    },
    {
        "video_id": "0r-zLJqVPsU",
        "title": "O Buldogue Inglês Mais Preguiçoso - Desenho Animado",
        "description": "Este buldogue inglês leva a preguiça a outro nível! Ele não corre, não late muito e prefere passar o dia inteiro descansando no sofá. Neste vídeo adorável, descubra por que esse cachorro é campeão mundial de sono e como sua preguiça é contagiante. Perfeito para crianças, em português do Brasil, com narração divertida e zero texto na tela.",
        "tags": "buldogue inglês,preguiça,sono,cachorro,cão,sofá,descanso,infantil,criancas,família,desenho animado,animacao,pet,cachorro preguiçoso"
    },
    {
        "video_id": "IRDspnBURFk",
        "title": "Dachshund Salsicha - Desenho Animado Infantil",
        "description": "Conheça a salsicha mais alongada e divertida que você já viu! O dachshund (ou cachorro salsicha) está aqui para alegrar seu dia com sua energia, curiosidade e corpo longo demais para caber em qualquer lugar. Neste desenho animado infantil, acompanhe suas aventuras cheias de humor e fofura. Em português do Brasil, para toda a família.",
        "tags": "dachshund,salsicha,cachorro,cão,desenho animado,infantil,criancas,família,animacao,pet,corpo longo,aventuras,humor,fofura"
    }
]

for v in videos:
    cmd = [
        sys.executable, "youtube_update.py",
        "--video-id", v["video_id"],
        "--title", v["title"],
        "--description", v["description"],
        "--tags", v["tags"],
        "--category", "24",
        "--client-secret", "client_secret.json",
        "--token", "youtube_token.json",
    ]
    print(f"Atualizando {v['video_id']} - {v['title'][:50]}...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("ERRO:", result.stderr)
    print("-" * 60)

print("Concluído para todos os vídeos!")
