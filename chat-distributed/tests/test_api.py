import unittest
from unittest.mock import MagicMock, patch
import json
import sys
import os

# Add chat-distributed to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from publisher.message_publisher import app

class TestAuthAPI(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    @patch('publisher.message_publisher.get_db_connection')
    def test_register_success(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        payload = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123"
        }
        response = self.app.post('/register', json=payload)
        self.assertEqual(response.status_code, 201)
        self.assertIn("User registered successfully", str(response.data))

    @patch('publisher.message_publisher.get_db_connection')
    def test_login_success(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock fetchone to return a user with a hashed password
        from werkzeug.security import generate_password_hash
        hashed = generate_password_hash("password123")
        mock_cursor.fetchone.return_value = {
            "user_id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "password": hashed,
            "status": "offline"
        }

        payload = {
            "email": "test@example.com",
            "password": "password123"
        }
        response = self.app.post('/login', json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Login successful", str(response.data))

    @patch('publisher.message_publisher.publish_message')
    def test_send_message_success(self, mock_publish):
        mock_publish.return_value = True
        payload = {
            "sender_id": 1,
            "room_id": 101,
            "content": "Hello World"
        }
        response = self.app.post('/send-message', json=payload)
        self.assertEqual(response.status_code, 202)
        self.assertIn("accepted", str(response.data))

if __name__ == '__main__':
    unittest.main()
