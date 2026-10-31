import json
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import login

class LoginTest(unittest.TestCase):
    def test_save_private_atomic(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'config/challonge.json'
            with patch.object(login, 'CONFIG', target):
                login.save({'access_token': 'fake'})
                self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
                self.assertEqual(json.loads(target.read_text())['access_token'], 'fake')
                self.assertEqual(list(target.parent.iterdir()), [target])

    def test_pending_and_slowdown_then_success(self):
        tokens = {'access_token': 'fake', 'refresh_token': 'fake-refresh', 'token_type': 'Bearer', 'scope': login.SCOPES}
        device = {'verification_uri': 'https://auth.challonge.com/oauth/device', 'user_code': 'TEST', 'device_code': 'private', 'expires_in': 300, 'interval': 2}
        with patch.object(login, 'request_json', side_effect=[device, login.OAuthError('authorization_pending'), login.OAuthError('slow_down'), tokens, {'data': {'type': 'user'}}]), patch.object(login.time, 'sleep') as sleep, patch.object(login, 'save') as save, patch('builtins.print'):
            login.device_login('fake-client')
            self.assertEqual([call.args[0] for call in sleep.call_args_list], [2, 2, 7])
            self.assertEqual(save.call_args.args[0]['auth_type'], 'oauth')

    def test_denied_does_not_save(self):
        device = {'verification_uri': 'https://auth.challonge.com/oauth/device', 'user_code': 'TEST', 'device_code': 'private', 'expires_in': 300}
        with patch.object(login, 'request_json', side_effect=[device, login.OAuthError('access_denied')]), patch.object(login.time, 'sleep'), patch.object(login, 'save') as save, patch('builtins.print'):
            with self.assertRaises(login.OAuthError):
                login.device_login('fake-client')
            save.assert_not_called()

    def test_missing_scope_does_not_validate(self):
        with patch.object(login, 'request_json') as request:
            with self.assertRaises(ValueError):
                login.validate_tokens({'access_token': 'fake', 'refresh_token': 'fake', 'token_type': 'Bearer', 'scope': 'me'})
            request.assert_not_called()

    def test_untrusted_verification_rejected(self):
        with patch.object(login, 'request_json', return_value={'verification_uri': 'https://evil.example/'}), patch('builtins.print') as output:
            with self.assertRaises(ValueError):
                login.device_login('fake-client')
            output.assert_not_called()

if __name__ == '__main__':
    unittest.main()

class BrowserTest(unittest.TestCase):
    def test_callback_state_and_destination(self):
        url = login.REDIRECT_URI + '?code=private&state=expected'
        self.assertEqual(login.callback_code(url, 'expected'), 'private')
        for candidate in (url.replace('localhost', 'evil.example'), url.replace('expected', 'wrong'), url + '&code=second'):
            with self.assertRaises(ValueError):
                login.callback_code(candidate, 'expected')

    def test_browser_uses_api_and_saves_only_after_validation(self):
        tokens = {'access_token': 'fake', 'refresh_token': 'fake', 'token_type': 'Bearer', 'scope': login.SCOPES}
        with patch.object(login.secrets, 'token_urlsafe', return_value='state'), patch.object(login.getpass, 'getpass', side_effect=['fake-secret', login.REDIRECT_URI + '?code=private&state=state']), patch.object(login, 'request_json', side_effect=[tokens, {'data': {'type': 'user'}}]) as request, patch.object(login, 'save') as save, patch('builtins.print'):
            login.browser_login('fake-client')
            self.assertEqual(request.call_args_list[0].args[0], 'https://api.challonge.com/oauth/token')
            self.assertEqual(save.call_args.args[0]['redirect_uri'], login.REDIRECT_URI)


class HeadersTest(unittest.TestCase):
    def test_authenticated_get_has_json_api_content_type(self):
        from io import BytesIO
        response = BytesIO(b'{"data":{"type":"user"}}')
        with patch.object(login.urllib.request, 'build_opener') as opener:
            opener.return_value.open.return_value.__enter__.return_value = response
            login.request_json('https://api.challonge.com/v2.1/me.json', token='fake')
            request = opener.return_value.open.call_args.args[0]
            self.assertEqual(request.get_header('Content-type'), 'application/vnd.api+json')
            self.assertEqual(request.get_header('Authorization-type'), 'v2')
            self.assertEqual(request.get_header('Authorization'), 'Bearer fake')
            self.assertIsNone(request.data)

    def test_token_post_keeps_form_content_type(self):
        from io import BytesIO
        with patch.object(login.urllib.request, 'build_opener') as opener:
            opener.return_value.open.return_value.__enter__.return_value = BytesIO(b'{}')
            login.request_json('https://api.challonge.com/oauth/token', {'code': 'fake'})
            request = opener.return_value.open.call_args.args[0]
            self.assertEqual(request.get_header('Content-type'), 'application/x-www-form-urlencoded')
