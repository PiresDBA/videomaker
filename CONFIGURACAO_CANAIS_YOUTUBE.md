# CONFIGURAÇÃO DE 3 CANAIS DO YOUTUBE (PT / EN / ES)

Este documento explica como configurar 3 canais separados do YouTube, um para cada idioma,
e como o sistema escolhe automaticamente o canal correto na hora de publicar.

## Visão geral

Cada idioma tem seu próprio canal do YouTube, com seu próprio `client_secret.json` e
`youtube_token.json` (OAuth2). O sistema escolhe as credenciais baseadas no idioma do vídeo:

| Idioma | Canal | client_secret | token OAuth2 |
|--------|-------|---------------|--------------|
| Português (padrão) | Canal principal | `scripts/client_secret_pt.json` | `scripts/youtube_token_pt.json` |
| Inglês | Canal inglês | `scripts/client_secret_en.json` | `scripts/youtube_token_en.json` |
| Espanhol | Canal espanhol | `scripts/client_secret_es.json` | `scripts/youtube_token_es.json` |

## Passo a passo para configurar cada canal

### 1. Criar projeto/client_secret no Google Cloud Console

Para **cada um dos 3 canais**, faça o seguinte:

1. Acesse https://console.cloud.google.com/
2. Crie um novo projeto (ex: "Videomaker PT", "Videomaker EN", "Videomaker ES")
3. Ative a API "YouTube Data API v3" no projeto
4. Crie credenciais OAuth2: "ID do cliente OAuth" → tipo "Aplicativo para computador"
5. Baixe o JSON e salve como:
   - `scripts/client_secret_pt.json` (canal português)
   - `scripts/client_secret_en.json` (canal inglês)
   - `scripts/client_secret_es.json` (canal espanhol)

### 2. Autorizar cada canal (primeiro upload)

Após salvar cada `client_secret_*.json`, rode o upload para esse idioma para gerar o token:

```powershell
# Canal português
python scripts/youtube_upload.py --client-secret scripts/client_secret_pt.json --token scripts/youtube_token_pt.json --video "qualquer_video.mp4"

# Canal inglês
python scripts/youtube_upload.py --client-secret scripts/client_secret_en.json --token scripts/youtube_token_en.json --video "qualquer_video.mp4"

# Canal espanhol
python scripts/youtube_upload.py --client-secret scripts/client_secret_es.json --token scripts/youtube_token_es.json --video "qualquer_video.mp4"
```

Na primeira execução de cada um, o navegador será aberto para você fazer login e autorizar o canal correspondente. O token será salvo automaticamente.

### 3. Verificar se os tokens foram criados

Após autorizar todos os 3 canais, deve existir na pasta `scripts\`:

```
client_secret_pt.json    youtube_token_pt.json
client_secret_en.json    youtube_token_en.json
client_secret_es.json    youtube_token_es.json
```

## Como funciona na prática

Quando você roda:

```powershell
python scripts/publish_multilang.py
```

O sistema processa cada projeto e, para cada idioma:
1. **pt**: usa `client_secret_pt.json` + `youtube_token_pt.json` → publica no canal português
2. **en**: usa `client_secret_en.json` + `youtube_token_en.json` → publica no canal inglês
3. **es**: usa `client_secret_es.json` + `youtube_token_es.json` → publica no canal espanhol

Cada vídeo sobe com título, descrição e legendas no idioma correto, no canal correto.

## Exemplo de fluxo completo

Para publicar um projeto novo que tem os 3 MP4s (pt, en, es):

```powershell
python scripts/publish_multilang.py
```

O sistema vai:
1. Detectar que o projeto tem os 3 MP4s
2. Fazer upload do MP4 pt para o canal português (com título/desc/legenda em PT)
3. Fazer upload do MP4 en para o canal inglês (com título/desc/legenda em EN)
4. Fazer upload do MP4 es para o canal espanhol (com título/desc/legenda em ES)
5. Marcar o projeto como concluído no histórico

## Arquivos envolvidos

| Arquivo | Função |
|---------|--------|
| `scripts/publish_multilang.py` | Orquestra o upload de cada idioma no seu canal |
| `scripts/youtube_upload.py` | Faz o upload real para o YouTube (usa as credenciais recebidas) |
| `scripts/youtube_captions.py` | Envia as legendas .srt para o YouTube |
| `CONFIGURACAO_CANAIS_YOUTUBE.md` | Este documento |

## Troubleshooting

**Erro 403 insufficientPermissions:** O token não tem o escopo `youtube.force-ssl`. Delete o `youtube_token_*.json` do canal com problema e rode novamente para reautorizar.

**O vídeo sobe no canal errado:** Verifique se você está usando o `client_secret_*.json` correto para cada idioma. O sistema seleciona automaticamente baseado no idioma, mas as credenciais devem estar corretas.

**Não quer criar 3 canais agora:** Você pode usar o mesmo `client_secret.json` e `youtube_token.json` para todos os idiomas. Basta renomear/copiar o arquivo existente para os 3 nomes (`_pt`, `_en`, `_es`) e todos irão para o mesmo canal.