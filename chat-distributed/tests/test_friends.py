import unittest
from unittest.mock import MagicMock, patch
import json
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../publisher')))

from message_publisher import app

class TestFriendsAPI(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    @patch('message_publisher.get_db_connection')
    def test_search_users(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock result for search
        mock_cursor.fetchall.return_value = [
            {'user_id': 2, 'username': 'otheruser', 'status': 'online'}
        ]

        response = self.app.get('/users/search?query=other&user_id=1')

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data['data']), 1)
        self.assertEqual(data['data'][0]['name'], 'otheruser')

    @patch('message_publisher.get_db_connection')
    def test_add_friend(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock check if already friends (return None = not friends)
        mock_cursor.fetchone.return_value = None

        payload = {'user_id': 1, 'friend_id': 2}
        response = self.app.post('/friends',
                               data=json.dumps(payload),
                               content_type='application/json')

        self.assertEqual(response.status_code, 201)
        self.assertIn("Friend added", response.get_json()['message'])

        # Verify bidirectional insert
        # We expect a single execute call with multiple values or multiple execute calls?
        # The implementation uses: "INSERT ... VALUES (%s, %s), (%s, %s)"
        mock_cursor.execute.assert_called()
        args = mock_cursor.execute.call_args[0]
        self.assertIn("INSERT INTO friends", args[0])
        # Check params (user_id, friend_id, friend_id, user_id)
        self.assertEqual(args[1], (1, 2, 2, 1))

    @patch('message_publisher.get_db_connection')
    def test_get_friends(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock fetchall
        mock_cursor.fetchall.return_value = [
            {'user_id': 2, 'username': 'friend1', 'status': 'offline'}
        ]

        response = self.app.get('/friends?user_id=1')

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data['data']), 1)
        self.assertEqual(data['data'][0]['name'], 'friend1')
