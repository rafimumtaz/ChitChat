import unittest
from unittest.mock import MagicMock, patch
import json
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../publisher')))

from message_publisher import app

class TestLogoutAPI(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    @patch('message_publisher.get_db_connection')
    def test_logout(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        payload = {'user_id': 1}
        response = self.app.post('/logout',
                               data=json.dumps(payload),
                               content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertIn('Logged out successfully', response.get_json()['message'])

        # Verify DB update status to offline
        mock_cursor.execute.assert_called_with(
            "UPDATE users SET status = 'offline' WHERE user_id = %s", (1,)
        )
        mock_conn.commit.assert_called()
