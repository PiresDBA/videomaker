# Referência de Personagens para Frida e Luna

## Visão Geral

A referência de personagens é um recurso crucial que ajuda o Gemini a manter consistência visual das personagens Frida (buldogue inglês) e Luna (dachshund) através de todos os vídeos gerados. Quando ativada, o Gemini usa uma imagem de referência anexada à conversa para gerar imagens que mantêm a aparência consistente das personagens.

## Como Funciona

### Fluxo de Trabalho:

1. **Configuração**: Uma imagem de referência é salva em `scripts/config.json` no campo `reference_image`
2. **Durante a geração de imagens**: O `fetch_images.py` lê a configuração e passa `--ref-image <path>` para `gemini_fetch.py`
3. **Anexação**: O `gemini_fetch.py` anexa a imagem de referência à conversa do Gemini antes de enviar o prompt
4. **Geração**: O Gemini usa a referência visual para gerar imagens consistentes

### Arquivos Principais:

- **`scripts/config.json`**: Configuração do Gemini, incluindo caminho da referência de personagens
- **`scripts/fetch_images.py`**: Script principal para geração de imagens, lê e passa a referência
- **`scripts/gemini_fetch.py`**: Script de automação do Gemini, anexa referência usando `attach_reference()`
- **`scripts/reference/frida_luna_reference.jpg`**: A imagem de referência real das personagens

## Problema: Referência Não Enviada ao Mudar Jimmy

### Sintoma:
Quando você cria uma nova conta no Jimmy (Chrome/Google account), a imagem de referência para Frida e Luna para de ser anexada à conversa do Gemini. As imagens ainda são geradas, mas sem a referência visual, resultando em inconsistência na aparência das personagens através dos vídeos.

### Causa:
A causa raiz é que a `reference_image` no `config.json` não é automaticamente configurada quando você faz login em uma nova conta do Jimmy. O `get_ref_image()` em `fetch_images.py` lê de `config.json`, e se o campo `reference_image` estiver vazio ou ausente, nenhuma referência é passada para o Gemini.

### Fluxo de Erro:

```
1. Novo Jimmy account criado (Chrome profile)
2. `get_ref_image()` em fetch_images.py lê config.json
3. `config["reference_image"]` está vazio (padrão)
4. `--ref-image` não é adicionado ao comando gemini_fetch
5. `grab_image()` em gemini_fetch.py recebe `ref_image=None`
6. `attach_reference()` nunca é chamada
7. Gemini gera imagens SEM referência visual
```

## Solução

### Método 1: Configure a Referência de Personagens Permanentemente

Execute este script para configurar a referência de personagens:

```bash
python setup_reference_image.py
```

Este script:

1. **Cria diretório**: `scripts/reference/`
2. **Salva placeholder**: `scripts/reference/frida_luna_reference.jpg` (placeholder)
3. **Atualiza config.json**: Adiciona `reference_image` com caminho absoluto

### Método 2: Configure a Referência Manualmente

Edite `scripts/config.json` manualmente:

```json
{
  "gemini_skill": "gemini_media_scraping-1.0.0.ipkg.json",
  "ffmpeg_dir": "ffmpeg",
  "project_dir": "..",
  "image_bank": "banco de imagens",
  "reference_image": "C:\videomaker\scripts\reference\frida_luna_reference.jpg"
}
```

### Método 3: Faça Login com a Mesma Conta do Jimmy Sempre

Para evitar a necessidade de reconfiguração, sempre faça login com a mesma conta do Jimmy que originalmente configurou a referência. Isso garante que a sessão do Chrome e a configuração permaneçam as mesmas.

## Como Subir uma Imagem de Referência Real

1. **Tire uma foto boa**:
   - Foto em alta resolução (recomendado: 1920x1080 ou maior)
   - Mostre Frida e Luna lado a lado ou em imagens separadas
   - Sem fundo distrativo ou elementos que possam confundir o Gemini

2. **Salve no local correto**:
   ```
   C:\videomaker\scripts\reference\frida_luna_reference.jpg
   ```

3. **Atualize config.json**:
   ```bash
   # Edit scripts/config.json
   # Altere "reference_image" para o caminho absoluto completo
   "reference_image": "C:\videomaker\scripts\reference\frida_luna_reference.jpg"
   ```

4. **Reinicie a sessão do Chrome**:
   ```bash
   python scripts/gemini_fetch.py --login
   ```

## Imagem de Referência de Exemplo

Template de referência de personagens ideal:

- **Formato**: JPG ou PNG
- **Tamanho**: 800x600px ou maior, menos de 5MB
- **Layout**: Duas fotos lado a lado ou em colunas
- **Assunto**: Frida (buldogue inglês) + Luna (dachshund marrom)
- **Fundo**: Fundo neutro, sem distrações
- **Qualidade**: Foco nítido, boa iluminação

```
[FRIDA: bulldog inglês, focinho curto, olhos doces]  [LUNA: dachshund marrom, orelhas erguidas]
     ^                                              ^
   Personagem 1                                Personagem 2
```

## Verificação

Para verificar se a referência está funcionando:

1. **Execute um pipeline**
2. **Verifique o log** (`logs/pipeline40/pipeline40_*.log`):
   ```
   2024-11-05 11:00:00  ref-image: imagem de referencia anexada (frida_luna_reference.jpg)
   ```
3. **Verifique as imagens geradas**: Todas devem mostrar a mesma aparência de Frida e Luna

## Troubleshooting

### Problema: Referência não anexada

Verifique `gemini_fetch.py` em `attach_reference()`:

```python
if not ref_path:
    return False  # ← ref_path está vazio!
```

**Solução**: Certifique-se de que `config.json` tem `reference_image` preenchido.

### Problema: Configuração não preservada ao mudar Jimmy

**Solução**: 

1. **Configure a referência permanentemente**: `python setup_reference_image.py`
2. **Documente o caminho**: Anote o caminho completo
3. **Reconfigure em novas contas**: Use o mesmo caminho sempre

### Problema: Imagem de referência ausente ou corrompida

**Solução**:

1. Verifique se `scripts/reference/frida_luna_reference.jpg` existe
2. Verifique se o arquivo não está vazio
3. Re-suba uma imagem válida

## Nota Técnica

### Por que a Referência Funciona:

O Gemini usa o contexto visual da imagem de referência para:

1. **Identificar raças**: Distinguir entre bulldog inglês vs dachshund
2. **Manter características**: Preservar características específicas (focinho curto, orelhas erguidas)
3. **Consistência de aparência**: Mesmas cores, texturas, poses através dos vídeos
4. **Melhorar qualidade**: Reduzir ambiguidade na geração de imagens

### Papel do Gemini_fetch.py:

```python
# Em grab_image()
if ref_image and not await attach_reference(page, ref_image):
    ref_image = None  # Fallback para modo texto apenas
```

A `attach_reference()` tenta anexar o arquivo usando:

1. **Input file**: `input[type="file"]` (se presente)
2. **Button click**: `button[aria-label*="attachment"]` (se input não encontrado)
3. **File chooser**: `page.expect_file_chooser()` (para upload via botão)

### Como a Referência Afeta os Prompts:

Quando a referência está anexada, o Gemini internalmente modifica:

- **Prompt de cena**: Mantém estrutura básica
- **Instruções de referência**: Adiciona "Ilustração fofa e divertida de desenho animado das duas personagens (cachorrinhas) da imagem de referência anexada"
- **Estilo**: Mantém regras anti-marca (proibido citar estúdios)

### Riscos da Ausência de Referência:

Sem referência, você pode experimentar:

- **Inconsistência entre cenas**: Frida às vezes parece bulldogue, às vezes parece outro cão
- **Mudanças de raça**: Luna às vezes parece salsicha, às vezes parece outro cão
- **Variação de aparência**: Olhos diferentes, cores diferentes, texturas diferentes
- **Quebras de continuidade**: Personagens parecem diferentes episódio a episódio

### Configuração de Referência Requerida:

Todos os pipelines REQUIREM `reference_image` em `config.json` para:

1. **Geração consistente**: Mesma aparência em todos os vídeos
2. **Qualidade consistente**: Mesmas informações visuais por prompt
3. **Contexto rico**: Mais contexto visual para o Gemini
4. **Estilo consistente**: Mesmas características visuais ao longo do tempo

Sem esta configuração, cada imagem tem chance de variar significativamente, quebrando a identidade visual da série de vídeos.

## Resumo

A solução simples e direta é executar:

```bash
python setup_reference_image.py
```

E subir uma foto de referência de alta qualidade de Frida e Luna em `scripts/reference/frida_luna_reference.jpg`.

Isso garante que a referência esteja sempre presente, independentemente de qual conta do Jimmy você use, e mantém a consistência visual das personagens em todos os vídeos gerados.

## Commandos Úteis

### Verificação da configuração:

```bash
# Verifique se config.json tem reference_image
cat scripts/config.json | grep -A 5 -B 5 reference_image

# Verifique se a referência existe
ls -la scripts/reference/

# Execute um pipeline rápido de teste (uma imagem)
python scripts/fetch_images.py --single s1
```

### Reparação rápida:

```bash
# Reconfigure referência
python setup_reference_image.py

# Reinicie a sessão do Chrome
python scripts/gemini_fetch.py --login

# Execute novamente o pipeline
python scripts/loop40.py --limit 1
```

### Limpeza e reconfigure:

```bash
# Remova referência antiga
rm -f scripts/reference/frida_luna_reference.jpg
rm -f scripts/config.json

# Reconfigure nova
python setup_reference_image.py
```

## Problemas Conhecidos

1. **Configuração não persiste após login do Chrome**: Sempre execute `python setup_reference_image.py` após login do Chrome
2. **Erro de caminho em Windows**: Use caminho absoluto completo, não relativo
3. **Tamanho do arquivo grande**: Reduza para menos de 5MB para melhor desempenho
4. **Formato de arquivo não suportado**: Apenas JPG/PNG/NEF funcionando

## Resumo Final

**Problema**: Referência não anexada ao mudar contas do Jimmy
**Causa**: Campo `reference_image` ausente/vazio em `config.json`
**Solução**: Configure permanentemente `scripts/reference/frida_luna_reference.jpg` no `config.json`
**Comando**: `python setup_reference_image.py` + suba a imagem real

Isso resolve o problema para todos os pipelines futuros, independentemente de qual conta do Jimmy você use!
