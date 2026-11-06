# -*- coding: utf-8 -*-
"""
Setup de autenticacao do YouTube para novo canal.

Executa o fluxo OAuth2:
1. Verifica se scripts/client_secret.json existe (baixe no Google Cloud Console).
2. Deleta token antigo (se houver) para forcar nova autorizacao com o novo canal.
3. Abre o navegador para voce autorizar o canal.
4. Salva o token em scripts/youtube_token.json.

Uso:
  python scripts/youtube_setup.py

Passos manuais (antes de rodar este script):
  1. Acesse https://console.cloud.google.com
  2. Crie ou selecione um projeto
  3. Ative a API "YouTube Data API v3"
  4. Crie credenciais: "ID do cliente OAuth" -> tipo "App para computador"
  5. Baixe o JSON e salve como scripts/client_secret.json
  6. Na tela de consentimento OAuth, adicione seu e-mail como "Usuario de teste"

Depois de rodar este script, o token fica salvo e pode ser reusado
pelos scripts youtube_upload.py e youtube_update.py sem novo login.
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser(description="Setup de autenticacao YouTube (OAuth2)")
    ap.add_argument("--client-secret", default=str(HERE / "client_secret.json"))
    ap.add_argument("--token", default=str(HERE / "youtube_token.json"))
    ap.add_argument("--reset-token", action="store_true",
                    help="deleta o token antigo antes de autorizar (recomendado ao trocar de canal)")
    a = ap.parse_args()

    client_secret = Path(a.client_secret)
    token_path = Path(a.token)

    if not client_secret.is_file():
        print("=" * 70)
        print("ERRO: client_secret.json nao encontrado em:", client_secret)
        print("=" * 70)
        print()
        print("PASSO A PASSO PARA OBTER O ARQUIVO:")
        print("  1. Acesse https://console.cloud.google.com")
        print("  2. Crie ou selecione um projeto")
        print("  3. Menu 'APIs e Servicos' > 'Biblioteca' > ative 'YouTube Data API v3'")
        print("  4. Menu 'APIs e Servicos' > 'Credenciais'")
        print("  5. Crie credenciais > 'ID do cliente OAuth' > tipo 'App para computador'")
        print("  6. Baixe o JSON e salve como:", client_secret)
        print("  7. Em 'Tela de consentimento OAuth', adicione seu e-mail como")
        print("     'Usuario de teste' (caso o projeto esteja em modo de teste)")
        print()
        print("Depois de salvar o client_secret.json, rode este script novamente.")
        return 1

    # Deleta token antigo para forçar nova autorização (útil ao trocar de canal)
    if a.reset_token and token_path.exists():
        token_path.unlink()
        print(f"Token antigo removido: {token_path}")

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("ERRO: bibliotecas do Google nao instaladas.")
        print("Instale com: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2")
        return 1

    SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
              "https://www.googleapis.com/auth/youtube.force-ssl"]

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                print("Token renovado automaticamente.")
            except Exception:
                creds = None
        if not creds or not creds.valid:
            print("Abrindo o navegador para autorizar o canal do YouTube...")
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), SCOPES)
            creds = flow.run_local_server(port=0)

    token_path.write_text(creds.to_json(), encoding="utf-8")
    print(f"\nAutenticacao concluida com sucesso!")
    print(f"Token salvo em: {token_path}")
    print("Voce pode agora usar youtube_upload.py e youtube_update.py sem novo login.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
