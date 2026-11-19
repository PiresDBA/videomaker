# 🎬 PROMPTS DOS 5 VÍDEOS — GERAR MANUALMENTE NO GOOGLE FLOW

**Projeto:** Fridóca e Luninha sozinhas em casa
**Motivo:** o Flow não conseguiu gerar os vídeos automaticamente após várias tentativas. Fallback = você gera manualmente e salva na pasta.

---

## 📁 ONDE SALVAR

Todos os 5 arquivos vão em:

```
C:\videomaker\projects\bulldogue-ingles-frida-e-dachshund-marrom-luna-fic\assets\images\gemini\scenes\
```

**Nomes exatos dos arquivos** (salve com estes nomes):

| # | Nome do arquivo | Duração | Momento no vídeo |
|---|---|---|---|
| 1 | `intro_8s.mp4` | 8s | Abertura (0s) |
| 2 | `meio_2min.mp4` | 8s | ~2 minutos |
| 3 | `meio_5min.mp4` | 8s | ~5 minutos |
| 4 | `meio_7min.mp4` | 8s | ~7 minutos |
| 5 | `final_subscribe.mp4` | 5-8s | Final (subscribe) |

---

## ⚙️ CONFIGURAÇÃO NO FLOW (para TODOS os 5)

- **Modelo:** Veo 3.1 Lite
- **Qualidade:** BAIXA (10 créditos por vídeo → dá para fazer os 5)
- **Duração:** 8 segundos (escrever "8 SEGUNDOS" no prompt)
- **Formato:** 16:9
- **Exportação:** 720p
- **Personagens:** use `@Frida` e `@Luna` (arro, sem colchetes) em TODO prompt
  - `@Frida` = buldogue inglesa fawn, grande e compacta, colar de pérolas
  - `@Luna` = dachshund/salsicha marrom-chocolate, comprida e baixa, coleira dourada
- **Anexar** a imagem de referência: `C:\videomaker\scripts\reference\frida_luna_reference.jpg`
- Sem humanos, sem outros cachorros, sem texto, sem marcas

---

## 1️⃣ intro_8s.mp4 — ABERTURA

```
Video animado de EXATAMENTE 8 SEGUNDOS, 16:9, estilo desenho 3D cinematografico para criancas. Use @Frida (buldogue inglesa fawn, grande e compacta, colar de perolas) e @Luna (dachshund marrom-chocolate comprida e baixa, coleira dourada). As duas acenam alegres para a camera na sala aconchegante da casa, sorrindo, com olhinhos brilhantes e movimentos fofos. Luz quente e feliz. Mesmos personagens da referencia em todos os quadros. Sem humanos, sem texto, sem marcas, sem outros cachorros. DURACAO: 8 SEGUNDOS.
```

---

## 2️⃣ meio_2min.mp4 — O SOFÁ CASTELO (~2 min)

Cena do roteiro s2: o sofá gigante virou castelo/caverna/trampolim.

```
Video animado de EXATAMENTE 8 SEGUNDOS, 16:9, estilo desenho 3D cinematografico para criancas. Use @Frida (buldogue inglesa fawn, grande e compacta, colar de perolas) e @Luna (dachshund marrom-chocolate comprida e baixa, coleira dourada). Na sala de estar, @Frida pega impulso e cai de barriga no sofa gigante, que afunda todo fofinho. @Luna, bem baixinha, passa correndo por baixo da almofada como se fosse um tunel e aparece do outro lado com uma almofada na cabeca. @Frida olha sem entender e as duas riem com o focinho. O sofa virou castelo, caverna e trampolim. Mesmos personagens da referencia em todos os quadros. Sem humanos, sem texto, sem marcas, sem outros cachorros. DURACAO: 8 SEGUNDOS.
```

---

## 3️⃣ meio_5min.mp4 — A PISTA DO TAPETE (~5 min)

Cena do roteiro s10: o tapete virou pista de corrida.

```
Video animado de EXATAMENTE 8 SEGUNDOS, 16:9, estilo desenho 3D cinematografico para criancas. Use @Frida (buldogue inglesa fawn, grande e compacta, colar de perolas) e @Luna (dachshund marrom-chocolate comprida e baixa, coleira dourada). Na sala, o tapete virou pista de corrida: @Luna da a largada com o corpo bem baixinho, quase encostando no chao, e corre em zigue-zague entre as pernas da mesa. @Frida tenta acompanhar trotando no seu ritmo, e quando vira rapido as orelhinhas balancam e batem na bochecha. As duas brincam felizes. Mesmos personagens da referencia em todos os quadros. Sem humanos, sem texto, sem marcas, sem outros cachorros. DURACAO: 8 SEGUNDOS.
```

---

## 4️⃣ meio_7min.mp4 — A CAMA QUENTINHA (~7 min)

Cena do roteiro s15: volta ao quarto, as duas na cama.

```
Video animado de EXATAMENTE 8 SEGUNDOS, 16:9, estilo desenho 3D cinematografico para criancas. Use @Frida (buldogue inglesa fawn, grande e compacta, colar de perolas) e @Luna (dachshund marrom-chocolate comprida e baixa, coleira dourada). No quarto aconchegante, @Frida sobe na cama pelo banquinho com calma e ajuda @Luna a subir, deixando um espaco quentinho. @Luna se enrola toda, virando uma bolinha marrom bem fofa. @Frida deita pertinho, encostando as costas quentinhas na amiga, e as duas fecham os olhinhos em paz, como dois travesseiros com orelhas. Luz suave do fim de tarde. Mesmos personagens da referencia em todos os quadros. Sem humanos, sem texto, sem marcas, sem outros cachorros. DURACAO: 8 SEGUNDOS.
```

---

## 5️⃣ final_subscribe.mp4 — FINAL / INSCREVA-SE

```
Video animado de 8 SEGUNDOS, 16:9, estilo desenho 3D cinematografico para criancas. Use @Frida (buldogue inglesa fawn, grande e compacta, colar de perolas) e @Luna (dachshund marrom-chocolate comprida e baixa, coleira dourada). As duas na sala aconchegante sorriem, acenam e fazem gracinhas felizes, com confete colorido caindo e uma atmosfera de final feliz. Elas olham para a camera com carinho como quem diz 'ate a proxima'. Sem texto, sem letras, sem logo do YouTube (o botao de subscribe e colocado depois na edicao). Mesmos personagens da referencia em todos os quadros. Sem humanos, sem marcas, sem outros cachorros. DURACAO: 8 SEGUNDOS.
```

---

## ✅ DEPOIS DE SALVAR

Quando os 5 arquivos estiverem na pasta, me avise aqui no chat. Eu:
1. Conferio os 5 MP4s (duração, resolução)
2. Injeto no `video_clips.json` (intro + 3 meio + final)
3. Gero a sonoplastia pela narração + efeitos de fundo + blur/foco
4. Rodo o compose/preprocess/render final
5. Entrego o vídeo completo
