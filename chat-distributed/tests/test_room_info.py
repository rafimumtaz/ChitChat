import unittest
from unittest.mock import MagicMock, patch
import json
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../publisher')))

from message_publisher import app

class TestRoomInfoAPI(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    @patch('message_publisher.get_db_connection')
    def test_get_room_info(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock room info fetch
        mock_cursor.fetchone.return_value = {
            'room_name': 'Test Room',
            'created_by': 1,
            'admin_name': 'admin_user'
        }

        # Mock members fetch
        mock_cursor.fetchall.return_value = [
            {'user_id': 1, 'username': 'admin_user', 'status': 'online'},
            {'user_id': 2, 'username': 'member_user', 'status': 'offline'}
        ]

        response = self.app.get('/room/101/info')
        self.assertEqual(response.status_code, 200)

        data = response.get_json()['data']
        self.assertEqual(data['room_name'], 'Test Room')
        self.assertEqual(data['admin_name'], 'admin_user')
        self.assertEqual(len(data['members']), 2)

    @patch('message_publisher.get_db_connection')
    def test_kick_member_success(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock room fetch for auth check
        mock_cursor.fetchone.return_value = {'created_by': 1}

        payload = {'user_id': 2, 'current_user_id': 1}
        response = self.app.post('/room/101/kick',
                               data=json.dumps(payload),
                               content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertIn("kicked successfully", response.get_json()['message'])

        # Verify delete call
        mock_cursor.execute.assert_any_call(
            "DELETE FROM room_members WHERE room_id = %s AND user_id = %s",
            ('101', 2)
        )

    @patch('message_publisher.get_db_connection')
    def test_kick_member_unauthorized(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock room fetch: created by user 1
        mock_cursor.fetchone.return_value = {'created_by': 1}

        # Request from user 3 (not admin)
        payload = {'user_id': 2, 'current_user_id': 3}
        response = self.app.post('/room/101/kick',
                               data=json.dumps(payload),
                               content_type='application/json')

        self.assertEqual(response.status_code, 403)
        self.assertIn("Unauthorized", response.get_json()['message'])
