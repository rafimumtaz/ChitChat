import unittest
from unittest.mock import MagicMock, patch
import json
import sys
import os

# Add publisher directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../publisher')))

from message_publisher import app

class TestAuthAPI(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    @patch('message_publisher.get_db_connection')
    def test_register_success(self, mock_get_db):
        # Mock DB connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        payload = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password123'
        }

        response = self.app.post('/register',
                               data=json.dumps(payload),
                               content_type='application/json')

        self.assertEqual(response.status_code, 201)
        self.assertIn('User registered successfully', response.get_json()['message'])

        # Verify DB calls
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called()

    @patch('message_publisher.get_db_connection')
    def test_login_success(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock fetchone to return user data
        # Structure: {'user_id': 1, 'username': 'testuser', 'email': 'test@example.com', 'password': 'hashed_pw', 'status': 'offline'}
        # The cursor in message_publisher.py is created with dictionary=True

        mock_cursor.fetchone.return_value = {
            'user_id': 1,
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'hashed_pw',
            'status': 'offline'
        }

        with patch('message_publisher.check_password_hash') as mock_check:
            mock_check.return_value = True

            payload = {
                'email': 'test@example.com',
                'password': 'password123'
            }

            response = self.app.post('/login',
                                   data=json.dumps(payload),
                                   content_type='application/json')

            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data['user']['username'], 'testuser')

            # Verify status update to 'online'
            mock_cursor.execute.assert_any_call(
                "UPDATE users SET status = 'online' WHERE user_id = %s", (1,)
            )
            mock_conn.commit.assert_called()
