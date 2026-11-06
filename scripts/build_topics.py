# -*- coding: utf-8 -*-
"""Gera topics.txt (365 assuntos) intercalando 7 series + 34 datas especiais.

DESCRICOES DOS PERSONAGENS (usadas em todos os roteiros e prompts de imagem
do canal Frida e Luna, para manter consistencia visual entre cenas):

LUNA (salsicha / dachshund fêmea):
- Salsicha fêmea, pelagem marrom-chocolate, pelo curto, liso e rente (padrão da raça).
- Tem uns 11 anos (aparência saudável, sem sinais exagerados de idade).
- Focinho coberto pelo mesmo pelo curto, com apenas alguns pelinhos brancos discretos no contorno.
- MUITO briguenta: late, reclama e cria caso por tudo.
- Ciumenta e possessiva: não deixa ninguém chegar perto do tutor.
- Quem manda no par é ela: a chefona da casa, apesar dos ~10 kg.
- Importante: NÃO peluda, sem pelos longos, sem barba, sem sobrancelhas longas (evita visual "wire-haired").
- Apelido carinhoso: Luninha (usar na narração com carinho, sem trocar o nome Luna).

FRIDA (buldogue inglesa fêmea):
- Buldogue inglesa fêmea grande (~30 kg), pelagem amarela-fawn (a cor clássica dos buldogues).
- Super tranquila, pacata e preguiçosa (e super gulosa).
- Obedece à Luna em TUDO: dócil e submissa à chefona marrom.
- No fundo, as duas são amiguinhas.
- Apelido carinhoso: Fridóca (usar na narração com carinho, sem trocar o nome Frida).

Essas descricoes são injetadas automaticamente em todos os prompts de imagem
por generate_scenes_and_prompts.py (via FRIDA_LUNA_DESC) quando o roteiro
é detectado como Frida e Luna.

"""

A = """A Frida e a Luna descobrem que o aspirador de pó é um monstro
Luna tenta pegar o biscoito que está em cima da geladeira
A Frida decide fazer dieta (e o petisco some do pote)
O dia em que a Luna cavou um túnel até a casa do vizinho
Frida contra o espelho: quem é esse cachorro bravo?
Frida e Luna tentam abrir a geladeira sozinhas
A Luna vira detetive: quem comeu o sanduíche?
Frida e Luna e a noite do trovão
O primeiro dia de chuva: as duas descobrem as poças
Frida tenta subir no sofá alto (missão impossível)
A Luna e o mistério da meia sumida
Frida e Luna organizam uma festa surpresa de aniversário
As duas contra o robô aspirador
A visita do gato valentão: Frida e Luna dão um jeito
Frida e Luna ficam sozinhas em casa por um dia inteiro
O dia em que a Frida aprendeu a nadar na piscina
Luna e a pizza voadora
Frida e Luna criam um clube secreto de cães
A grande fuga do banho: Frida e Luna contra a banheira
Frida e Luna vão ao salão de beleza pet
Segunda-feira: Frida e Luna não querem sair da cama
Frida finge um machucado para ganhar petisco
Luna descobre o que tem atrás da porta de vidro
Frida e Luna disputam a caminha mais fofa
O carteiro misterioso: por que ele vem todo dia?
Luna usa o celular do tutor e liga para a pizzaria
Frida e Luna e a bolinha que sumiu debaixo do sofá
A Frida vira chef e o petisco vira um desastre
Luna tenta ensinar a Frida a correr (a Frida prefere rolar)
As duas escondem o osso... e esquecem onde
O dia em que Frida e Luna trocaram de lugar
Frida e Luna contra a mosca invencível
Luna e o grande segredo do pote de petiscos
A mudança de casa: Frida e Luna e as caixas misteriosas
Frida e Luna tentam ficar acordadas até a meia-noite
O dia em que a Luna quis ser gato
Frida e a árvore que não queria soltar o graveto
Luna e o aniversário esquecido da Frida
A Luna descobre o que é uma escada
Frida e Luna e o gato do vizinho que não sai do muro
Dia de faxina: Frida e Luna ajudam (ou atrapalham)
Frida e Luna contra o ventilador que faz vento
O dia em que acabou a energia
Luna aprende o truque de dar a pata (do jeito dela)
Frida tenta passar despercebida pela cozinha
O grande concurso de latidos do bairro
Frida e Luna e o presente embrulhado que não era delas
Luna e o mistério do barulho no armário
Frida e Luna descobrem o poder do olhar de dó
A caminha nova que ninguém quer usar
O dia em que a Frida decidiu virar atleta
Luna e o balão que não podia estourar
Frida e Luna e a bola gigante do parque
Duas amigas, um bicho de pelúcia e uma grande briga
Frida e Luna e a visita da tia com perfume forte
Frida e Luna e o primeiro cubo de gelo
O dia em que Frida e Luna foram ao cinema (da sala)
Luna e a pipoca fujona
Frida e Luna e a grande maratona de sonecas
Frida e Luna descobrem o que é fim de semana
Luna e o papagaio que imita o latido
Frida e Luna e o espirro que virou barulhão
Frida e o latido que sumiu
Frida e Luna e o jardim secreto atrás do muro
Luna e a minhoca que queria ser amiga
Frida e Luna na viagem de carro: quem vai na janela?
Frida e Luna e o ladrão de meias do varal
Luna e o espantalho que parecia vivo
Frida e Luna e a caixa de papelão misteriosa
Frida e Luna ganham um irmãozinho filhote
Frida e Luna e o relógio da hora do jantar""".split("\n")

B = """Por que o cachorro gira antes de deitar?
Por que cachorros inclinam a cabeça quando você fala?
Por que o cachorro lambe o seu rosto?
Por que cachorros cheiram o bumbum uns dos outros?
Por que o cachorro uiva quando ouve uma sirene?
Por que o cachorro abana o rabo? O que cada movimento significa
Por que o cachorro enterra comida e ossos?
Por que o cachorro come grama?
Por que o cachorro se sacode todo quando está molhado?
Por que o cachorro fica tão feliz quando você chega em casa?
Por que o cachorro sonha e mexe as patinhas dormindo?
Por que o cachorro te segue até no banheiro?
Os superpoderes do nariz do cachorro
O que os cachorros enxergam? As cores do mundo canino
Quantas palavras um cachorro entende de verdade?
Por que cachorros bocejam quando você boceja?
Por que o cachorro faz zoomies de repente?
Por que cachorros roubam seus chinelos e meias?
Por que o cachorro fica te olhando fixo enquanto você come?
Cachorros têm ciúmes? Veja o que a ciência descobriu
Por que o cachorro fareja tudo na rua?
Por que o cachorro late para o nada à noite?
Por que o cachorro tem medo de aspirador e secador?
Por que o cachorro escolhe uma pessoa favorita?
Por que o cachorro dorme em cima dos seus pés?
Por que o cachorro empurra você com o focinho?
Por que o cachorro esconde o brinquedo favorito?
Por que o cachorro faz carinha de pidão?
Por que o cachorro fica de língua para fora?
Por que cachorro adora passear de carro?
Por que o cachorro cava o sofá e a cama?
Por que o cachorro espirra quando está brincando?
Por que o cachorro suspira fundo e deita?
Por que cachorros se estranham e depois viram amigos?
Por que o cachorro corre atrás do próprio rabo?
Por que o cachorro late para a televisão?
Por que o cachorro fica de barriga para cima?
Por que cachorro de focinho curto ronca?
Como o cachorro sabe a hora que você chega?
Por que o cachorro traz o brinquedo mas não solta?
Para que servem os bigodes do cachorro?
Por que os cachorros têm tantos tamanhos e cores?
Do lobo ao sofá: como os cachorros viraram nossos amigos
Por que o cachorro fica com cara de culpado depois da bagunça?
Por que o cachorro abana o rabo para um lado ou para o outro?
Por que o nariz do cachorro é molhado e gelado?
Por que o cachorro adora rolar em coisas fedidas?
Por que o cachorro faz xixi em cada poste?
Um ano de cachorro vale sete anos de gente? Mito ou verdade
Cachorros entendem quando a gente está triste?""".split("\n")

C = """E se os cachorros pudessem falar por um dia?
Frida e Luna viram super-heroínas da vizinhança
Um dia na vida de um cachorro, do ponto de vista dele
A escola dos cachorros: o primeiro dia de aula
Frida e Luna encontram um mapa do tesouro no quintal
E se os cachorros mandassem na casa?
E se a Frida e a Luna tivessem emprego?
E se o mundo fosse do tamanho de um cachorro?
Luna, a salsicha, e a confusão na barraca de cachorro-quente
Frida e Luna viajam para a Lua
Frida e Luna descobrem um portal dentro do armário
Frida e Luna e a máquina de fazer petiscos
A cidade onde só moram cachorros
Frida e Luna detetives: o caso do osso dourado
O dia em que um cachorro virou prefeito
Frida e Luna e o submarino de banheira
Frida e Luna na selva: pequenas exploradoras
Frida e Luna no reino dos biscoitos
Frida e Luna astronautas na cozinha espacial
Frida e Luna e o cachorro-robô
Frida e Luna viajam no tempo e conhecem o primeiro cachorro do mundo
Frida e Luna num mundo de gigantes
A varinha mágica de petiscos
O campeonato de cães mais maluco do mundo
Frida e Luna e o circo dos animais
A banda dos cachorros: Frida na bateria e Luna no violão
Frida e Luna no restaurante dos cães
Frida e Luna e o castelo de almofadas
A corrida de trenó no sofá
O gênio da coleira: três desejos para Frida e Luna
Frida e Luna no parque de diversões dos cachorros
O biscoito que fala
O dia sem nenhum "não"
O reino dos cachorros preguiçosos
Frida e Luna no mundo ao contrário
A ilha dos ossos: Frida e Luna piratas
Frida e Luna cozinham para a rainha dos cães
Frida e Luna e o telescópio das estrelas
A fábrica de cócegas
Frida e Luna e a montanha de bolinhas""".split("\n")

D = """Hachiko: o cachorro que esperou o dono por 9 anos
Balto e Togo: os cães que salvaram uma cidade na neve
Cães-guia: os olhos de quem não enxerga
Cães de resgate: como eles encontram pessoas depois de terremotos
Bobbie: o cachorro que voltou para casa a pé por milhares de quilômetros
O cachorro que fez amizade com uma família de patinhos
O filhote que ganhou um lar no Natal
Cães terapeutas: os abraços que alegram hospitais
O cachorro que avisou a família a tempo (e virou herói)
Cães policiais e bombeiros: a equipe de quatro patas
A cachorrinha de três patas que adora correr
Do abrigo para uma vida nova: a adoção que mudou tudo
Cachorros que ajudam crianças a aprender a ler
Amizade improvável: o cachorro e o gatinho que viraram melhores amigos
O cachorro que esperava o ônibus escolar todos os dias
Greyfriars Bobby: o cachorrinho fiel de Edimburgo
Stubby: o cachorrinho que virou herói de uniforme
Rin Tin Tin: o cachorro que virou astro de cinema
Cães polares: os exploradores do gelo
Cães farejadores: os detetives dos aeroportos
Cães pastores: os maestros do rebanho
Cães salva-vidas: os nadadores que ajudam na água
Iditarod: a grande corrida de cães de trenó
Dez profissões de quatro patas
Cães no Egito Antigo: amigos dos faraós
Os cachorros escondidos em quadros famosos
Os cães que viraram prefeitos de verdade
Chaser: a cachorra que aprendeu mil palavras
Belka e Strelka: as cachorrinhas que voltaram do espaço
Cães de assistência: amigos que ajudam no dia a dia
Cães farejadores na floresta: como encontram quem se perdeu
Cães que protegem ovelhas: guardiões do campo
Fiéis para sempre: histórias de lealdade de cães pelo mundo
Cachorros atletas: agility, frisbee e mergulho
Cães surfistas e skatistas: os atletas mais fofos do mundo
Os cachorros da Pré-História: os primeiros amigos do homem
Cães e idosos: a amizade que aquece o coração
O cachorro que virou mascote da cidade
Cães que trabalham nas fazendas do Brasil
O vira-lata que virou campeão""".split("\n")

E = """Bulldog inglês: o cachorro mais preguiçoso e fofo do mundo
Salsicha: o caçador de texugos de patinhas curtas
Golden Retriever: por que ele é o melhor amigo do mundo
Husky siberiano: o cachorro que conversa e faz drama
Pug: o palhaço da família
Border Collie: o cachorro mais inteligente do planeta
Chihuahua: pequeno no tamanho, gigante na coragem
Vira-lata caramelo: o herói do Brasil
São Bernardo: o cachorro que resgata pessoas nos Alpes
Pastor Alemão: o guardião mais leal
Shih Tzu: o cachorrinho da realeza chinesa
Corgi: o cachorro de patinhas curtas que conquistou a realeza britânica
Labrador: o cachorro que ama água e comida
Dálmata: por que ele nasce branco e ganha pintinhas?
Poodle: o cachorro mais esperto que parece fresco
Yorkshire: pequenininho, mas manda em tudo
Maltês: o cachorrinho de algodão
Lhasa Apso: o pequeno guardião dos monges
Lulu da Pomerânia: a bolinha de pelo mais corajosa
Pinscher: o valente de bolso
Beagle: o nariz mais curioso do mundo
Cocker Spaniel: as orelhas mais lindas do mundo
Boxer: o eterno filhote que nunca para
Rottweiler: o gigante que é um bobão
Doberman: elegante, rápido e atento
Dogue Alemão: o gigante gentil
Akita: o cachorro que ficou famoso pela lealdade
Shiba Inu: o cachorro que faz careta
Chow-chow: o leãozinho de língua azul
Samoieda: o cachorro que sempre sorri
Malamute do Alasca: o puxador de trenó
Terra Nova: o urso nadador
Boiadeiro de Berna: o doce montanhês
Basset Hound: as orelhas que varrem o chão
Greyhound: o mais rápido dos cachorros
Jack Russell: o pequeno foguete
Schnauzer: o cachorro de bigode
Fila Brasileiro: o guardião do Brasil
Buldogue francês: o morcego fofo
Pastor de Shetland: o mini pastor esperto
Weimaraner: o fantasma cinza
Setter Irlandês: o cachorro de pelo de seda
Papillon: o cachorro com orelhas de borboleta
Bichon Frisé: a nuvenzinha animada
Cavalier King Charles: o cachorrinho dos nobres
Basenji: o cachorro que não late
Boston Terrier: o cavalheiro de smoking
Collie: o cachorro que virou estrela das telas
Pastor Belga: o atleta incansável
Whippet: o velocista de sofá""".split("\n")

F = """Como ensinar seu cachorro a sentar, dar a pata e ficar
Como brincar com seu cachorro do jeito certo
Como saber se o seu cachorro está feliz
Passeios seguros: como levar o cachorro para passear
Como receber um filhote novo em casa
O que fazer quando o cachorro tem medo de fogos
Como ensinar uma criança a tratar bem um cachorro
Como cuidar com carinho do seu velhinho de patas
Hora do banho: como deixar o cachorro feliz na água
Como escovar os dentes do seu cachorro (sem drama)
Cachorros e calor: como deixar o seu pet confortável no verão
Cachorros e frio: precisa de roupinha mesmo?
Como montar o cantinho perfeito do seu cachorro
Dez brinquedos caseiros para o seu cachorro
Jogos de nariz: brincadeiras de farejar em casa
Como ensinar o cachorro a não pular nas visitas
Como ensinar o cachorro a vir quando chamado
Como o cachorro aprende: o poder do petisco e do elogio
Como ajudar o cachorro a ficar sozinho com tranquilidade
Como apresentar um cachorro novo aos outros bichinhos da casa
Caça ao tesouro de petiscos: brincadeira para fazer em casa
A linguagem do cachorro: o que as orelhas dizem
A linguagem do cachorro: o que o corpo diz
Como cumprimentar um cachorro que você não conhece
Como passear com mais de um cachorro sem enrolar a guia
Como acostumar o cachorro a andar de carro com tranquilidade
A rotina de um cachorro feliz: sono, passeio e brincadeira
Dia de chuva: como entreter o cachorro em casa
Cachorro e criança: cinco regras de ouro para brincar juntos
Como escolher o nome perfeito para o seu cachorro
Como o cachorro escolhe a caminha (e como ajudar)
A primeira ida ao veterinário: como deixar o cachorro tranquilo
Alimentos que cachorro não pode comer: o que todo mundo precisa saber
Como ensinar o cachorro a pegar e trazer a bolinha
Como ensinar o cachorro a ficar quieto sem gritar
Como fazer uma festa de aniversário para o cachorro
O que o seu cachorro faz enquanto você trabalha
Como tirar fotos incríveis do seu cachorro
Viajando com o cachorro: o que levar na mala
Como a gente conversa com o cachorro: palavras, gestos e carinho""".split("\n")

SAGAS = [
    ("Saga do Osso de Ouro", ["o mapa misterioso", "a floresta do quintal", "o guardião do tesouro", "o grande final"]),
    ("Saga da Ilha dos Biscoitos Perdidos", ["o naufrágio da cozinha", "a praia de migalhas",
                                             "o vulcão de pasta de amendoim", "o banquete final"]),
    ("Saga da Casa que Range", ["os barulhos da madrugada", "pistas no corredor", "o suspeito número um",
                                "a verdade por trás da porta"]),
    ("Saga da Viagem Mais Maluca do Mundo", ["quem trancou a mala?", "uma parada inesperada", "a pousada dos bichos",
                                             "a chegada à praia"]),
    ("Saga do Campeonato Mundial de Cães", ["a inscrição", "o treino mais desastrado", "a grande rival",
                                            "o dia da final"]),
    ("Saga da Escola de Heróis Peludos", ["a carta misteriosa", "as provas do primeiro dia", "o desafio do recreio",
                                          "a formatura"]),
    ("Saga do Circo que Chegou à Cidade", ["a lona colorida", "os ensaios", "o número que deu errado",
                                           "o espetáculo da noite"]),
    ("Saga da Expedição ao Fundo do Quintal", ["o equipamento de exploradoras", "a trilha das formigas",
                                               "a toca misteriosa", "a descoberta"]),
    ("Saga do Dia sem Petiscos", ["o pote vazio", "a investigação nas casas", "o culpado inesperado",
                                  "petiscos para todos"]),
    ("Saga do Castelo da Rainha das Almofadas", ["a convocação real", "a ponte de travesseiros",
                                                 "o enigma do trono", "a coroa de pelúcia"]),
]
G = ["%s (%d/4): %s" % (name, i + 1, part) for name, parts in SAGAS for i, part in enumerate(parts)]

DATED = """01-06|Dia de Reis: Frida e Luna seguem a estrela
01-01|Ano Novo: as resoluções da Frida e da Luna
01-21|Dia do Abraço: o abraço mais difícil da Frida
02-06|Carnaval: Frida e Luna caem na folia
02-09|Carnaval: o bloco dos cachorros
03-22|Dia da Água: Luna e a torneira que pinga
03-28|Páscoa: a caça aos ovos mais bagunçada do mundo
04-01|Dia da Mentira: a pegadinha da Luna
04-18|Dia do Livro Infantil: Frida e Luna e a biblioteca encantada
04-22|Dia da Terra: Frida e Luna plantam uma árvore
04-28|Dia do Cão-Guia: a história de um herói de coleira
05-01|Dia do Trabalho: o primeiro emprego da Frida e da Luna
05-09|Dia das Mães: Frida e Luna e o presente para a mamãe
05-25|Dia da Adoção: a família que escolheu a Frida e a Luna
06-05|Dia do Meio Ambiente: Frida e Luna e o quintal sem lixo
06-12|Dia dos Namorados: a Luna e o cachorro do vizinho
06-24|Festa junina: as duas e a pipoca misteriosa
07-02|Dia do Bombeiro: Frida e Luna visitam o quartel
07-20|Dia do Amigo: Frida e Luna, amigas para sempre
08-08|Dia dos Pais: Frida e Luna e o presente do papai
08-13|Sexta-feira 13: Frida e Luna e o azar que não existe
08-22|Dia do Folclore: Frida e Luna e as lendas do quintal
08-26|Dia Internacional do Cachorro: a festa de todos os cães
09-07|Independência: Frida e Luna no desfile da vizinhança
09-09|Dia do Veterinário: Frida e Luna e o doutor mais querido
09-21|Dia da Árvore: a árvore que abrigava todo mundo
10-04|Dia dos Animais: a festa de todos os bichinhos
10-12|Dia das Crianças: Frida e Luna e a festa no quintal
10-15|Dia do Professor: Frida e Luna e a aula mais divertida
10-31|Halloween: Frida e Luna e a casa mal-assombrada dos petiscos
11-13|Dia da Gentileza: Frida e Luna e o gesto mais bonito do bairro
12-24|A véspera de Natal da Frida e da Luna
12-25|O Natal da Frida e da Luna: o presente perdido
12-31|Réveillon: a coragem da Luna na noite dos fogos""".split("\n")

SERIES = [A, B, C, D, E, F, G]


def interleave(series):
    """Espalha as series de modo uniforme, preservando a ordem interna de cada uma."""
    n = sum(len(s) for s in series)
    keyed = []
    for si, s in enumerate(series):
        for k, item in enumerate(s):
            keyed.append(((k + 0.5) * n / len(s), si, k, item))
    keyed.sort()
    return [x[3] for x in keyed]


def main():
    assert [len(s) for s in SERIES] == [71, 50, 40, 40, 50, 40, 40], [len(s) for s in SERIES]
    assert len(DATED) == 34
    seq = interleave(SERIES)
    allt = seq + [d.split("|", 1)[1] for d in DATED]
    low = [t.casefold() for t in allt]
    assert len(allt) == 365 and len(set(low)) == 365, (len(allt), len(set(low)))
    assert max(len(t) for t in allt) <= 100
    head = """# Fila de 365 assuntos do canal (1 por dia, por 1 ano).
# - Linhas comuns saem na ordem, uma por dia. As séries estão intercaladas (comédia, curiosidades,
#   fantasia, histórias reais, raças, convivência e sagas em partes) para o canal não ficar repetitivo.
# - Linhas com "@MM-DD" são datas especiais: saem exatamente naquele dia (ex.: @12-25 = Natal).
#   Se o dia passar sem rodar, elas voltam na fila quando acabarem as linhas comuns.
# - Para acrescentar mais assuntos, cole novas linhas no FINAL. Linhas com # e linhas vazias são ignoradas.
"""
    dated = sorted(DATED)
    lines = [head] + seq + [""] + ["# ----- datas especiais -----"] + ["@%s %s" % tuple(d.split("|", 1)) for d in dated]
    open("topics.txt", "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("OK", len(seq), "comuns +", len(dated), "datadas")


if __name__ == "__main__":
    main()
