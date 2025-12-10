import unittest
from unittest.mock import MagicMock, patch
import json
import sys
import os
import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../publisher')))

from message_publisher import app

class TestMessagesAPI(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    @patch('message_publisher.get_db_connection')
    def test_get_messages(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock fetchall for messages
        # Structure: message_id, content, created_at, sender_id, username
        mock_cursor.fetchall.return_value = [
            {
                'message_id': 1001,
                'content': 'Hello world',
                'created_at': datetime.datetime(2023, 1, 1, 12, 0, 0),
                'sender_id': 1,
                'username': 'testuser'
            }
        ]

        response = self.app.get('/messages?room_id=101')

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data['data']), 1)
        self.assertEqual(data['data'][0]['content'], 'Hello world')
        self.assertEqual(data['data'][0]['sender']['name'], 'testuser')
        self.assertEqual(data['data'][0]['timestamp'], '12:00 PM')
