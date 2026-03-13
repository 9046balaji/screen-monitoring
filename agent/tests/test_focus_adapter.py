import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Ensure agent can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from enforcer import poll_focus_sessions

@patch('enforcer.get_db_connection')
@patch('focus_mode.start_focus_session')
def test_poll_focus_sessions(mock_start_focus, mock_get_db):
    # Setup mock db
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    
    # Mock return rows
    mock_cursor.fetchall.return_value = [
        {'id': '123', 'duration_minutes': 60}
    ]
    
    poll_focus_sessions()
    
    # Verify update to running was executed
    mock_cursor.execute.assert_any_call('UPDATE focus_sessions SET status = "running" WHERE id = ?', ('123',))
    mock_conn.commit.assert_called()
    
    # Verify focus mode was triggered
    mock_start_focus.assert_called_once_with(duration_minutes=60, session_name="Commitment Focus")
