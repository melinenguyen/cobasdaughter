import json
import os
import unittest
from unittest.mock import MagicMock, patch
from dashboard import pulse_data as p


class DataTests(unittest.TestCase):
    @patch.dict(os.environ, {'BRAND_PULSE_TOKEN_KEY': 'test-only-key',
        'GOOGLE_CLIENT_ID': 'id', 'GOOGLE_CLIENT_SECRET': 'secret'})
    @patch('dashboard.pulse_data.requests.post')
    def test_refresh_preserves_refresh_token_and_encrypts(self, post):
        db = MagicMock()
        encrypted = p.cipher().encrypt(json.dumps({'refresh_token': 'keep-private'}).encode()).decode()
        post.return_value.json.return_value = {'access_token': 'new-private', 'expires_in': 3600}
        result = p.refresh(db, 'google_search_console', 'site', encrypted)
        self.assertEqual(result['refresh_token'], 'keep-private')
        stored = db.execute.call_args.args[1][0]
        self.assertNotIn('new-private', stored)
        self.assertEqual(json.loads(p.cipher().decrypt(stored.encode()))['access_token'], 'new-private')
        db.commit.assert_called_once()

    @patch('dashboard.pulse_data.requests.post')
    def test_tiktok_paginates_and_deduplicates(self, post):
        first, second = MagicMock(), MagicMock()
        video = {'id': '1', 'create_time': 1720000000, 'like_count': 8}
        first.json.return_value = {'error': {'code': 'ok'}, 'data': {'videos': [video], 'has_more': True, 'cursor': 20}}
        second.json.return_value = {'error': {'code': 'ok'}, 'data': {'videos': [video], 'has_more': False}}
        post.side_effect = [first, second]
        db = MagicMock()
        state, detail = p.tiktok(db, 'account', {'access_token': 'token'})
        self.assertEqual(state, 'success')
        self.assertIn('1 authorized', detail)
        self.assertEqual(post.call_args.kwargs['json']['cursor'], 20)
        self.assertEqual(db.execute.call_count, 2)
        self.assertIsNone(db.execute.call_args.args[1][-1])  # Missing views are not zero.

    @patch('dashboard.pulse_data.requests.post')
    def test_failed_tiktok_preserves_previous_data(self, post):
        post.return_value.json.return_value = {'error': {'code': 'access_token_invalid'}}
        db = MagicMock()
        with self.assertRaises(ValueError):
            p.tiktok(db, 'account', {'access_token': 'token'})
        db.execute.assert_not_called()

    @patch('dashboard.pulse_data.requests.post')
    def test_google_uses_brand_filter_and_final_data(self, post):
        post.return_value.json.return_value = {'rows': []}
        db = MagicMock()
        state, detail = p.google(db, 'sc-domain:cobasdaughter.com', {'access_token': 'token'})
        body = post.call_args.kwargs['json']
        self.assertEqual(body['dataState'], 'final')
        self.assertEqual(body['dimensions'], ['date'])
        self.assertIn('daughter', body['dimensionFilterGroups'][0]['filters'][0]['expression'])
        self.assertIn('0 reported days', detail)
        self.assertEqual(db.execute.call_count, 1)  # No invented zero rows.


if __name__ == '__main__':
    unittest.main()
