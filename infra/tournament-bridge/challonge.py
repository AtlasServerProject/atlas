"""Bounded Challonge JSON:API client with private OAuth renewal."""
import json
import time
import urllib.request
import urllib.error
import login

class ApiError(Exception):
    def __init__(self, status):
        self.status = status
        super().__init__('Challonge HTTP ' + str(status))

class Client:
    def __init__(self):
        self.credentials = json.loads(login.CONFIG.read_text())

    def refresh(self):
        c = self.credentials
        fields = {'grant_type': 'refresh_token', 'refresh_token': c['refresh_token'], 'client_id': c['client_id']}
        for key in ('client_secret', 'redirect_uri'):
            if c.get(key):
                fields[key] = c[key]
        tokens = login.request_json('https://api.challonge.com/oauth/token', fields)
        if not tokens.get('access_token') or not tokens.get('refresh_token'):
            raise ValueError('Invalid OAuth renewal')
        self.credentials = {**c, **tokens, 'created_at': int(tokens.get('created_at', time.time()))}
        login.save(self.credentials)

    def call(self, method, path, payload=None, refreshed=False):
        if not refreshed and time.time() >= float(self.credentials.get('created_at', 0)) + float(self.credentials.get('expires_in', 0)) - 120:
            self.refresh()
            refreshed = True
        request = urllib.request.Request('https://api.challonge.com/v2.1' + path,
            data=None if payload is None else json.dumps(payload).encode(), method=method,
            headers={'Authorization-Type': 'v2', 'Authorization': 'Bearer ' + self.credentials['access_token'],
                     'Content-Type': 'application/vnd.api+json', 'Accept': 'application/json', 'User-Agent': 'Atlas-Tournaments/1.0'})
        try:
            with urllib.request.build_opener(login.NoRedirect).open(request, timeout=20) as response:
                raw = response.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as error:
            if error.code == 401 and not refreshed:
                self.refresh()
                return self.call(method, path, payload, True)
            if error.code == 422:
                self.validation_error = json.loads(error.read(65536))
            raise ApiError(error.code) from None

def body(kind, **attributes):
    return {'data': {'type': kind, 'attributes': attributes}}
