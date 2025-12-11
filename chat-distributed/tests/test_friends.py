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

        # Default: exclude friends
        response = self.app.get('/users/search?query=other&user_id=1')
        self.assertEqual(response.status_code, 200)

        # Verify SQL contains NOT IN clause for default behavior
        args = mock_cursor.execute.call_args[0]
        self.assertIn("NOT IN", args[0])

    @patch('message_publisher.get_db_connection')
    def test_search_users_include_friends(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchall.return_value = [
            {'user_id': 2, 'username': 'frienduser', 'status': 'online'}
        ]

        # include_friends=true
        response = self.app.get('/users/search?query=friend&user_id=1&include_friends=true')
        self.assertEqual(response.status_code, 200)

        # Verify SQL does NOT contain NOT IN clause
        args = mock_cursor.execute.call_args[0]
        self.assertNotIn("NOT IN", args[0])

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
        self.assertIn("Friend request sent", response.get_json()['message'])

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
