import sys
import os
import unittest
from unittest.mock import patch, mock_open, MagicMock

# Adjust sys.path so we can import trashclaw
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import trashclaw

class TestPipeCommand(unittest.TestCase):
    def setUp(self):
        trashclaw.HISTORY.clear()
        
    @patch('builtins.print')
    def test_pipe_no_args(self, mock_print):
        res = trashclaw.handle_slash('/pipe')
        self.assertTrue(res)
        mock_print.assert_called_with("  Usage: /pipe <filename>")

    @patch('builtins.print')
    def test_pipe_no_history(self, mock_print):
        res = trashclaw.handle_slash('/pipe out.txt')
        self.assertTrue(res)
        mock_print.assert_called_with("  No previous response to pipe.")

    @patch('builtins.print')
    @patch('builtins.open', new_callable=mock_open)
    def test_pipe_success(self, mock_file, mock_print):
        trashclaw.HISTORY.append({"role": "user", "content": "hello"})
        trashclaw.HISTORY.append({"role": "assistant", "content": "world output"})
        
        # mock _resolve_path since we care about the output
        with patch('trashclaw._resolve_path', return_value='/fake/out.txt'):
            res = trashclaw.handle_slash('/pipe out.txt')
            self.assertTrue(res)
            
            mock_file.assert_called_once_with('/fake/out.txt', 'w', encoding='utf-8')
            mock_file().write.assert_called_once_with("world output")
            mock_print.assert_any_call("  Piped last response to /fake/out.txt")

if __name__ == '__main__':
    unittest.main()
