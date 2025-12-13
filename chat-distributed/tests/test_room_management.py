import unittest
from unittest.mock import MagicMock, patch
import json
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../publisher')))

from message_publisher import app

class TestRoomManagementAPI(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    @patch('message_publisher.get_db_connection')
    def test_delete_room(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock room auth check (user 1 is creator)
        mock_cursor.fetchone.return_value = {'created_by': 1}

        payload = {'current_user_id': 1}
        response = self.app.delete('/room/101',
                                 data=json.dumps(payload),
                                 content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertIn("Room deleted", response.get_json()['message'])

        # Verify delete call
        mock_cursor.execute.assert_any_call("DELETE FROM chatrooms WHERE room_id = %s", ('101',))

    @patch('message_publisher.get_db_connection')
    def test_clear_chat(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock auth
        mock_cursor.fetchone.return_value = {'created_by': 1}

        payload = {'current_user_id': 1}
        response = self.app.delete('/room/101/messages',
                                 data=json.dumps(payload),
                                 content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertIn("Chat cleared", response.get_json()['message'])

        # Verify delete call
        mock_cursor.execute.assert_any_call("DELETE FROM messages WHERE room_id = %s", ('101',))

    @patch('message_publisher.get_db_connection')
    def test_invite_member(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock check membership (returns None = not member)
        # Fix: Mock return values as dicts to match DictCursor usage
        mock_cursor.fetchone.side_effect = [None, {'username': 'SenderName'}, {'room_name': 'RoomName'}]

        payload = {'room_id': 101, 'user_id': 2, 'sender_id': 1}
        response = self.app.post('/chatrooms/invite',
                               data=json.dumps(payload),
                               content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertIn("Invitation sent", response.get_json()['message'])
