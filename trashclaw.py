# Changes to trashclaw.py
# Add these at the top of the file (after existing imports):

# --- TOML/JSON config support ---
import os
import json

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # optional third-party fallback
    except ImportError:
        tomllib = None  # will fall back to JSON


def load_project_config():
    """
    Load .trashclaw.toml (preferred) or .trashclaw.json from the current
    working directory.  Returns a plain dict; missing file => empty dict.

    Supported keys
    --------------
    context_files : list[str]   – paths auto-loaded into conversation context
    system_prompt : str         – appended to the system prompt
    model         : str         – overrides the default/env model name
    auto_shell    : bool        – skip shell-command approval prompts
    """
    config = {}

    # ---- Try .trashclaw.toml first ----
    toml_path = os.path.join(os.getcwd(), '.trashclaw.toml')
    if os.path.isfile(toml_path):
        if tomllib is not None:
            try:
                with open(toml_path, 'rb') as fh:
                    config = tomllib.load(fh)
                return config
            except Exception as e:
                print(f'[trashclaw] Warning: could not parse {toml_path}: {e}')
        else:
            # tomllib unavailable – try a minimal manual parse for simple cases
            # and warn the user
            print(
                '[trashclaw] Warning: tomllib not available (Python < 3.11 and '
                'tomli not installed). Trying .trashclaw.json instead.'
            )

    # ---- Fall back to .trashclaw.json ----
    json_path = os.path.join(os.getcwd(), '.trashclaw.json')
    if os.path.isfile(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as fh:
                config = json.load(fh)
            return config
        except Exception as e:
            print(f'[trashclaw] Warning: could not parse {json_path}: {e}')

    return config


def apply_project_config(config, agent_state):
    """
    Apply values loaded by load_project_config() to *agent_state*.

    agent_state is expected to be the dict / object that TrashClaw uses to
    hold runtime state.  The keys touched are:

        agent_state['model']           – model name string
        agent_state['auto_shell']      – bool, skip shell approval
        agent_state['system_prompt']   – base system prompt string
        agent_state['messages']        – conversation history list

    All modifications are additive / overriding only when a key is present
    in the config, so existing defaults are untouched when keys are absent.
    """
    if not config:
        return

    # ---- model override ----
    if 'model' in config:
        agent_state['model'] = str(config['model'])
        print(f"[trashclaw] Config: model set to '{agent_state['model']}'")

    # ---- auto_shell ----
    if 'auto_shell' in config:
        agent_state['auto_shell'] = bool(config['auto_shell'])
        if agent_state['auto_shell']:
            print('[trashclaw] Config: auto_shell enabled (shell commands run without approval)')

    # ---- system_prompt append ----
    if 'system_prompt' in config:
        extra = str(config['system_prompt'])
        # append to whatever system prompt is already set
        existing = agent_state.get('system_prompt', '')
        agent_state['system_prompt'] = (existing + '\n\n' + extra).strip()
        print(f'[trashclaw] Config: system_prompt appended ({len(extra)} chars)')

    # ---- auto-load context_files ----
    if 'context_files' in config:
        files = config['context_files']
        if not isinstance(files, list):
            print('[trashclaw] Warning: context_files must be a list – skipping')
            return

        loaded = []
        for rel_path in files:
            abs_path = os.path.join(os.getcwd(), rel_path)
            if not os.path.isfile(abs_path):
                print(f'[trashclaw] Warning: context file not found: {rel_path}')
                continue
            try:
                with open(abs_path, 'r', encoding='utf-8', errors='replace') as fh:
                    content = fh.read()
                # Inject as a user→assistant exchange so it sits in history
                # naturally and does not look like a new turn.
                agent_state['messages'].append({
                    'role': 'user',
                    'content': (
                        f'[auto-loaded context file: {rel_path}]\n\n'
                        f'```\n{content}\n```'
                    )
                })
                agent_state['messages'].append({
                    'role': 'assistant',
                    'content': f'I have loaded `{rel_path}` into context and will reference it as needed.'
                })
                loaded.append(rel_path)
            except Exception as e:
                print(f'[trashclaw] Warning: could not read {rel_path}: {e}')

        if loaded:
            print(f"[trashclaw] Config: auto-loaded context files: {', '.join(loaded)}")


# ---------------------------------------------------------------------------
# Integration point – add the following lines inside the existing startup /
# main() function of trashclaw.py, AFTER agent_state is initialised but
# BEFORE the interactive loop begins.
# ---------------------------------------------------------------------------
#
# Example (pseudo-diff showing where to insert):
#
#   agent_state = {
#       'model': os.environ.get('TRASHCLAW_MODEL', DEFAULT_MODEL),
#       'auto_shell': False,
#       'system_prompt': BASE_SYSTEM_PROMPT,
#       'messages': [],
#       ...  (other existing keys)
#   }
#
# + # --- Load per-project config ---
# + _project_cfg = load_project_config()
# + apply_project_config(_project_cfg, agent_state)
# +
#   # ... existing .trashclaw.md loading ...
#   # ... interactive loop ...
