#!/usr/bin/env python3
"""Challonge device OAuth setup. Credentials never appear in arguments or logs."""
import getpass
import json
import os
import secrets
from pathlib import Path
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

CONFIG = Path.home() / '.config/atlas/challonge.json'
SCOPES = 'me tournaments:read tournaments:write participants:read participants:write matches:read matches:write'

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

class OAuthError(Exception):
    def __init__(self, code):
        self.code = code

def request_json(url, fields=None, token=None):
    headers = {'Accept': 'application/json', 'Content-Type': 'application/vnd.api+json',
               'User-Agent': 'Atlas-Tournament-Setup/1.0'}
    body = None
    if fields is not None:
        body = urllib.parse.urlencode(fields).encode()
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
    if token:
        headers.update({'Authorization-Type': 'v2', 'Authorization': 'Bearer ' + token})
    request = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        try:
            code = json.loads(error.read(65536)).get('error')
        except (ValueError, AttributeError):
            code = None
        if code in ('authorization_pending', 'slow_down', 'access_denied', 'expired_token', 'invalid_grant', 'invalid_client', 'invalid_scope', 'invalid_request'):
            raise OAuthError(code) from None
        raise OAuthError('http_' + str(error.code)) from None

def save(credentials):
    CONFIG.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix='.challonge-', dir=CONFIG.parent)
    try:
        with os.fdopen(fd, 'w') as output:
            json.dump(credentials, output)
            output.write('\n')
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, CONFIG)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

def validate_tokens(tokens):
    if not isinstance(tokens, dict) or not isinstance(tokens.get('access_token'), str) or not tokens['access_token']:
        raise ValueError('invalid token response')
    if tokens.get('token_type', '').lower() != 'bearer' or not tokens.get('refresh_token'):
        raise ValueError('invalid token response')
    if not set(SCOPES.split()).issubset(set(tokens.get('scope', '').split())):
        raise ValueError('missing scopes')
    user = request_json('https://api.challonge.com/v2.1/me.json', token=tokens['access_token'])
    if not isinstance(user.get('data'), dict) or user['data'].get('type') != 'user':
        raise ValueError('invalid user response')

def device_login(client_id):
    device = request_json('https://connect.challonge.com/oauth/authorize_device',
                          {'client_id': client_id, 'scope': SCOPES})
    verification = device['verification_uri']
    parsed = urllib.parse.urlsplit(verification)
    if parsed.scheme != 'https' or parsed.hostname not in ('auth.challonge.com', 'connect.challonge.com') or parsed.username or parsed.password:
        raise ValueError('invalid verification URL')
    print('\nAbra no navegador:', verification)
    print('Informe o código:', device['user_code'])
    print('Confira a conta e autorize o aplicativo Atlas. Aguardando autorização...')
    deadline = time.monotonic() + min(900, max(1, int(device['expires_in'])))
    interval = max(2, int(device.get('interval', 5)))
    while time.monotonic() < deadline:
        time.sleep(min(interval, max(0, deadline - time.monotonic())))
        if time.monotonic() >= deadline:
            break
        try:
            tokens = request_json('https://connect.challonge.com/oauth/token', {
                'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
                'device_code': device['device_code'], 'client_id': client_id,
            })
        except OAuthError as error:
            if error.code == 'authorization_pending':
                continue
            if error.code == 'slow_down':
                interval += 5
                continue
            raise
        validate_tokens(tokens)
        save({'auth_type': 'oauth', 'client_id': client_id, **tokens})
        return
    raise OAuthError('expired_token')

REDIRECT_URI = 'https://localhost:8765/challonge/callback'

def callback_code(url, state):
    parsed = urllib.parse.urlsplit(url)
    expected = urllib.parse.urlsplit(REDIRECT_URI)
    query = urllib.parse.parse_qs(parsed.query)
    if (parsed.scheme, parsed.netloc, parsed.path) != (expected.scheme, expected.netloc, expected.path):
        raise ValueError('invalid callback')
    if query.get('state') != [state] or len(query.get('code', [])) != 1 or not query['code'][0]:
        raise ValueError('invalid callback state or code')
    return query['code'][0]

def browser_login(client_id):
    secret = getpass.getpass('Client Secret atual do aplicativo (oculto): ').strip()
    if not secret or any(ord(c) < 33 or ord(c) > 126 for c in secret):
        raise ValueError('invalid secret')
    state = secrets.token_urlsafe(32)
    url = 'https://api.challonge.com/oauth/authorize?' + urllib.parse.urlencode({
        'client_id': client_id, 'redirect_uri': REDIRECT_URI,
        'response_type': 'code', 'scope': SCOPES, 'state': state,
    })
    print('Configure e salve este OAuth URL no aplicativo Challonge:', REDIRECT_URI)
    print('Abra este endereço no navegador e autorize o Atlas:')
    print(url)
    print('Ao redirecionar para localhost, a página poderá informar conexão recusada.')
    print('Copie o endereço COMPLETO da barra do navegador e cole abaixo, somente neste terminal.')
    callback = getpass.getpass('Endereço completo após autorizar (oculto): ').strip()
    code = callback_code(callback, state)
    try:
        tokens = request_json('https://api.challonge.com/oauth/token', {
            'grant_type': 'authorization_code', 'client_id': client_id, 'client_secret': secret,
            'redirect_uri': REDIRECT_URI, 'code': code,
        })
    except OAuthError as error:
        print('Falha na troca do código por token.')
        raise
    try:
        validate_tokens(tokens)
    except OAuthError:
        print('O token foi recebido, mas a API recusou a validação da conta.')
        raise
    save({'auth_type': 'oauth', 'client_id': client_id, 'client_secret': secret,
          'redirect_uri': REDIRECT_URI, 'token_endpoint': 'https://api.challonge.com/oauth/token', **tokens})

def main():
    if sys.argv[1:] not in (['login'], ['login', '--browser']):
        print('Uso: atlas-challonge login [--browser]')
        return 2
    if not sys.stdin.isatty():
        print('Execute em um terminal interativo.')
        return 2
    client_id = getpass.getpass('Client ID do aplicativo Challonge (oculto): ').strip()
    if not client_id or any(ord(char) < 33 or ord(char) > 126 for char in client_id):
        print('Client ID inválido; nenhuma alteração foi feita.')
        return 1
    try:
        if '--browser' in sys.argv:
            browser_login(client_id)
        else:
            device_login(client_id)
    except OAuthError as error:
        messages = {'invalid_client': 'Challonge recusou o Client ID/Client Secret. Confira se pertencem ao mesmo aplicativo e use o segredo atual.', 'invalid_scope': 'Challonge recusou as permissões solicitadas.', 'invalid_request': 'Challonge recusou os parâmetros da autorização.', 'access_denied': 'Autorização recusada.', 'expired_token': 'Código expirado. Execute o login novamente.',
                    'invalid_grant': 'Código inválido ou expirado. Execute o login novamente.'}
        print(messages.get(error.code, 'Challonge não concluiu a autorização (' + error.code + '). Tente novamente.'))
        return 1
    except (OSError, ValueError, KeyError, TypeError):
        print('Não foi possível validar ou salvar a autorização. Nenhuma credencial da resposta será exibida.')
        return 1
    print('Challonge autenticado. Tokens salvos com acesso restrito ao seu usuário.')
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except (KeyboardInterrupt, EOFError):
        print('\nConfiguração cancelada.')
        sys.exit(1)
