# SPDX-License-Identifier: MIT

import os
from datetime import datetime
from commands.base import BaseCommand


class PipeCommand(BaseCommand):
    def __init__(self, history):
        super().__init__()
        self.history = history

    def execute(self, args):
        """Save last assistant response to file"""
        if not self.history:
            print("No conversation history available to save.")
            return

        # Find the last assistant message
        last_assistant_msg = None
        for msg in reversed(self.history):
            if msg.get('role') == 'assistant':
                last_assistant_msg = msg.get('content', '')
                break

        if not last_assistant_msg:
            print("No assistant response found in history.")
            return

        # Determine filename
        if args:
            filename = ' '.join(args)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"response_{timestamp}.txt"

        try:
            # Write to file
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(last_assistant_msg)

            # Get file size
            file_size = os.path.getsize(filename)
            abs_path = os.path.abspath(filename)

            print(f"Saved to: {abs_path}")
            print(f"Size: {file_size} bytes")

        except Exception as e:
            print(f"Error saving file: {e}")
