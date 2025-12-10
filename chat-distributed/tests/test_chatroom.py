import unittest
from unittest.mock import MagicMock, patch
import json
import sys
import os

# Add chat-distributed to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from publisher.message_publisher import app

class TestChatroomAPI(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    @patch('publisher.message_publisher.get_db_connection')
    def test_create_chatroom_success(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock lastrowid for room_id
        mock_cursor.lastrowid = 101

        payload = {
            "room_name": "Test Room",
            "created_by": 1
        }
        response = self.app.post('/create-room', json=payload)
        self.assertEqual(response.status_code, 201)
        self.assertIn("Chatroom created successfully", str(response.data))

        # Verify SQL calls
        # 1. Insert chatroom
        # 2. Insert member
        self.assertEqual(mock_cursor.execute.call_count, 2)

    @patch('publisher.message_publisher.get_db_connection')
    def test_get_chatrooms_success(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchall.return_value = [
            {'room_id': 101, 'room_name': 'Test Room', 'created_by': 1}
        ]

        response = self.app.get('/chatrooms?user_id=1')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['data']), 1)
        self.assertEqual(data['data'][0]['name'], 'Test Room')

if __name__ == '__main__':
    unittest.main()
