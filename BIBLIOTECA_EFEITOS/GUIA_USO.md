# Biblioteca de Efeitos de Movimento — Guia para o Pipeline

Pasta: `C:\videomaker\BIBLIOTECA_EFEITOS\`
Gerada: 2026-11-18. Use como REFERÊNCIA: aqui estão os MP4s de demonstração
(3s cada, 960x540) e os PNGs em `assets/`.

## Regra de ouro
Efeitos dão **vida** à imagem sem roubar a cena. NUNCA aplicar zoom/Ken Burns
em imagens-colagem (2/3/4 painéis) — corta os painéis. O movimento vem das
partículas, não da câmera.

## Efeitos disponíveis e quando usar (inteligência do pipeline)

| Efeito | Gatilho na NARRAÇÃO / cena | MP4 |
|---|---|---|
| `bolinhas_sabao` | cenas felizes, água, banho, brincadeira leve, alegria | `bolinhas_sabao.mp4` |
| `folhinhas_vento` | parque, gramado, árvores, vento, passeio ao ar livre | `folhinhas_vento.mp4` |
| `estrelinhas` | mágica, feitiço, surpresa, "algo mágico", noite, sonho | `estrelinhas.mp4` |
| `abelhinhas` | flores, jardim, mel, primavera, natureza feliz | `abelhinhas.mp4` |
| `coracoes` | amor, carinho, amizade, abraço, "fique com a gente" | `coracoes.mp4` |
| `ossinhos` | osso, brincar com osso, cachorro feliz com osso | `ossinhos.mp4` |
| `racao_varios_formatos` | ração, comida, biscoito, almoço, fome, petisco | `racao_varios_formatos.mp4` |
| `soninho_zzz` | sono, dormir, cochilo, cansaço, noite, sonhar | `soninho_zzz.mp4` |
| `chuva` | chuva, tempestade, água caindo, dia chuvoso | `chuva.mp4` |
| `fumacinha` | neblina, fumaça, mistério, cena suave/calma, suspense leve | `fumacinha.mp4` |
| `passarinhos` | céu, passarinho, pássaro, voar, canto dos pássaros | `passarinhos.mp4` |

## Como o pipeline deve escolher
1. Ler o texto do BEAT (narration) e extrair palavras-chave.
2. Casar com a tabela acima (1 efeito principal por beat; pode combinar 2 leves).
3. Aplicar via overlay PNG animado (ver `criar_efeitos_final_v2.py`), nunca zoom.
4. Se o beat não casar com nenhum, usar `bolinhas_sabao` ou `folhinhas_vento`
   (neutros e alegres) — ou nenhum, se a cena for very emocional/séria.

## Arquivos
- `assets/*.png` — partículas transparentes (bolha, folha, estrela, coração,
  abelha, osso, racao_*, zzz, gota, passaro, fumaca).
- `*.mp4` — demonstrações de 3s (para aprovação visual).
- `BIBLIOTECA.jpg` — folha de contato com frames t=0.3 e t=2.5 de cada efeito.
- Script gerador: `scripts/criar_efeitos_final_v2.py`.

## Status
Aprovados pelo usuário em 2026-11-18: todos os 11 efeitos (versão v2,
distribuição em toda a tela, fumaça orgânica, 10x+ elementos).
