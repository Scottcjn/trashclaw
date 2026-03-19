import os
import json
import sys

def load_project_config():
    """
    Read .trashclaw.toml (or .trashclaw.json) project config 
    that auto-loads specified files into context on startup.
    """
    config = {}
    if os.path.exists('.trashclaw.toml'):
        try:
            try:
                import tomllib
                with open('.trashclaw.toml', 'rb') as f:
                    config = tomllib.load(f)
            except ImportError:
                import tomli as toml
                with open('.trashclaw.toml', 'rb') as f:
                    config = toml.load(f)
        except Exception as e:
            print(f"Error reading .trashclaw.toml: {e}", file=sys.stderr)
    elif os.path.exists('.trashclaw.json'):
        try:
            with open('.trashclaw.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            print(f"Error reading .trashclaw.json: {e}", file=sys.stderr)
            
    return config

def auto_load_context(config):
    """
    Auto-loads specified files into context on startup based on config.
    """
    context = []
    files = config.get('context_files', config.get('files', config.get('context', [])))
    if isinstance(files, list):
        for file_path in files:
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        context.append({'path': file_path, 'content': f.read()})
                        print(f"Auto-loaded context file: {file_path}")
                except Exception as e:
                    print(f"Error reading context file {file_path}: {e}", file=sys.stderr)
            else:
                print(f"Context file not found: {file_path}", file=sys.stderr)
    return context

def initialize_trashclaw():
    config = load_project_config()
    context = auto_load_context(config)
    return config, context

if __name__ == '__main__':
    config, context = initialize_trashclaw()
    print(f"Trashclaw initialized with {len(context)} context files auto-loaded.")
