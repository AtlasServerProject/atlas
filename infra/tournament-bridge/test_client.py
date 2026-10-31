import time
import unittest
from unittest.mock import patch
from challonge import Client

class RenewalTests(unittest.TestCase):
    def test_refresh_rotates_both_tokens_privately(self):
        client=Client.__new__(Client)
        client.credentials={'client_id':'fake','client_secret':'fake-secret','refresh_token':'old','access_token':'old-access'}
        with patch('login.request_json',return_value={'access_token':'new','refresh_token':'rotated','expires_in':604800}),patch('login.save') as save:
            client.refresh()
            self.assertEqual(client.credentials['refresh_token'],'rotated')
            self.assertEqual(save.call_args.args[0]['access_token'],'new')
    def test_incomplete_refresh_preserves_existing_credentials(self):
        client=Client.__new__(Client);client.credentials={'client_id':'fake','refresh_token':'old','access_token':'old-access'}
        with patch('login.request_json',return_value={'access_token':'incomplete'}),patch('login.save') as save:
            with self.assertRaises(ValueError):client.refresh()
            save.assert_not_called();self.assertEqual(client.credentials['refresh_token'],'old')
