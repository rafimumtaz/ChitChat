import unittest
from unittest.mock import MagicMock, patch
import json
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../publisher')))

from message_publisher import app

class TestNotificationsAPI(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    @patch('message_publisher.get_db_connection')
    def test_get_notifications(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchall.return_value = [
            {'notif_id': 1, 'type': 'FRIEND_REQUEST', 'sender_name': 'testuser', 'status': 'unread'}
        ]

        response = self.app.get('/notifications?user_id=1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()['data']), 1)

    @patch('message_publisher.get_db_connection')
    def test_respond_friend_request(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock notif fetch
        mock_cursor.fetchone.side_effect = [
            # first call for notification details
            {'notif_id': 1, 'type': 'FRIEND_REQUEST', 'sender_id': 2, 'receiver_id': 1},
            # second call for username (emit)
            {'username': 'sender'}
        ]

        payload = {'action': 'ACCEPT'}
        response = self.app.post('/notifications/1/respond',
                               data=json.dumps(payload),
                               content_type='application/json')

        self.assertEqual(response.status_code, 200)

        # Verify friends update
        mock_cursor.execute.assert_any_call(
            "UPDATE friends SET status = 'ACCEPTED' WHERE user_id = %s AND friend_id = %s",
            (2, 1)
        )

        # Verify notif update
        mock_cursor.execute.assert_any_call(
            "UPDATE notifications SET status = 'read' WHERE notif_id = %s",
            ('1',)
        )

    @patch('message_publisher.get_db_connection')
    def test_invite_to_room(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        payload = {'room_id': 101, 'user_id': 2, 'sender_id': 1}
        response = self.app.post('/chatrooms/invite',
                               data=json.dumps(payload),
                               content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertIn("Invitation sent", response.get_json()['message'])
