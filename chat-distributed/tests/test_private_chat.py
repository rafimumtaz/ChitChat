import unittest
from unittest.mock import MagicMock, patch
import json
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../publisher')))

from message_publisher import app

class TestPrivateChatAPI(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    @patch('message_publisher.get_db_connection')
    def test_start_private_chat_new(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock check for existing room: return None
        mock_cursor.fetchone.return_value = None

        # Mock creation ID
        mock_cursor.lastrowid = 202

        payload = {'user_id': 1, 'friend_id': 2}
        response = self.app.post('/private-chat',
                               data=json.dumps(payload),
                               content_type='application/json')

        self.assertEqual(response.status_code, 201)
        self.assertIn("Private chat started", response.get_json()['message'])

        # Verify transaction: 1 create room, 1 insert members
        # check call to insert chatrooms
        # check call to insert members
        mock_conn.commit.assert_called()

    @patch('message_publisher.get_db_connection')
    def test_add_chatroom_member(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock check if already member: None
        mock_cursor.fetchone.return_value = None

        payload = {'room_id': 101, 'user_id': 3}
        response = self.app.post('/chatrooms/add-member',
                               data=json.dumps(payload),
                               content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertIn("Member added", response.get_json()['message'])

        mock_cursor.execute.assert_called_with(
            "INSERT INTO room_members (room_id, user_id) VALUES (%s, %s)",
            (101, 3)
        )
