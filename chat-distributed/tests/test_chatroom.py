import unittest
from unittest.mock import MagicMock, patch
import json
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../publisher')))

from message_publisher import app

class TestChatroomAPI(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    @patch('message_publisher.get_db_connection')
    def test_create_room(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock insert result
        mock_cursor.lastrowid = 101

        payload = {
            'room_name': '#test-room',
            'created_by': 1
        }

        response = self.app.post('/create-room',
                               data=json.dumps(payload),
                               content_type='application/json')

        self.assertEqual(response.status_code, 201)
        self.assertIn('Chatroom created', response.get_json()['message'])

        # Verify transaction
        mock_cursor.execute.assert_any_call(
            "INSERT INTO chatrooms (room_name, created_by, type) VALUES (%s, %s, %s)",
            ('#test-room', 1, 'group')
        )
        mock_cursor.execute.assert_any_call(
            "INSERT INTO room_members (room_id, user_id) VALUES (%s, %s)",
            (101, 1)
        )
        mock_conn.commit.assert_called()

    @patch('message_publisher.get_db_connection')
    def test_get_chatrooms(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock fetchall - the endpoint formats the response using "data" key wrapping the list
        mock_cursor.fetchall.return_value = [
            {'room_id': 1, 'room_name': '#general', 'created_by': 1, 'timestamp': '2023-01-01'}
        ]

        response = self.app.get('/chatrooms')

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data['data']), 1)
        self.assertEqual(data['data'][0]['name'], '#general')
