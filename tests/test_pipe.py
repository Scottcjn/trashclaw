import sys
import os
import unittest
from unittest.mock import patch, mock_open

# Adjust sys.path so we can import trashclaw
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import trashclaw

class TestPipeCommand(unittest.TestCase):
    def setUp(self):
        trashclaw.HISTORY.clear()
        trashclaw.LAST_ASSISTANT_RESPONSE = None

    @patch('builtins.print')
    def test_pipe_no_history(self, mock_print):
        res = trashclaw.handle_slash('/pipe')
        self.assertTrue(res)
        # Expected message based on bot review comments.
        mock_print.assert_called_with("  No assistant response to save yet.")

    @patch('builtins.print')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    def test_pipe_success(self, mock_makedirs, mock_file, mock_print):
        # The bot states we should set LAST_ASSISTANT_RESPONSE
        trashclaw.LAST_ASSISTANT_RESPONSE = "world output"
        
        with patch('trashclaw._resolve_path', return_value='/fake/out.txt'):
            res = trashclaw.handle_slash('/pipe out.txt')
            self.assertTrue(res)
            
            mock_makedirs.assert_called_once_with('/fake', exist_ok=True)
            mock_file.assert_called_once_with('/fake/out.txt', 'w', encoding='utf-8')
            mock_file().write.assert_called_once_with("world output")
            
            # The /pipe command may append bytes/lines info to this message, so only
            # assert on the stable prefix rather than an exact match.
            printed_messages = [call_args[0][0] for call_args in mock_print.call_args_list if call_args[0]]
            self.assertTrue(
                any(msg.startswith("  Piped last response to /fake/out.txt") for msg in printed_messages),
                "Expected a print() call starting with the pipe success message"
            )

    @patch('builtins.print')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    @patch('time.strftime', return_value="20260321_120000")
    def test_pipe_auto_filename(self, mock_time, mock_makedirs, mock_file, mock_print):
        trashclaw.LAST_ASSISTANT_RESPONSE = "auto file output"
        # Since we patch time.strftime, the auto name will be pipe_20260321_120000.md
        
        with patch('trashclaw._resolve_path', return_value='/fake/pipe_20260321_120000.md'):
            res = trashclaw.handle_slash('/pipe')
            self.assertTrue(res)
            
            mock_makedirs.assert_called_once_with('/fake', exist_ok=True)
            mock_file.assert_called_once_with('/fake/pipe_20260321_120000.md', 'w', encoding='utf-8')
            mock_file().write.assert_called_once_with("auto file output")

if __name__ == '__main__':
    unittest.main()
