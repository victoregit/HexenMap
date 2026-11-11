"""Presentation-only localization. Persistent IDs and saved data stay unchanged."""
from functools import lru_cache
import json
import os
from pathlib import Path
import sys
import tempfile

LANGUAGES = {'pt-BR': 'Português (Brasil)', 'en-US': 'English'}


def language_path():
    """Use the installation's original user directory, including elevated startup."""
    home = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[2]
    try:
        pointer = home / 'state-dir.txt'
        if pointer.exists():
            state = Path(pointer.read_text(encoding='utf-8-sig').strip())
            if state.is_absolute():
                return state.parent / 'language.json'
    except (OSError, ValueError):
        pass
    return Path(os.environ.get('LOCALAPPDATA', str(home))) / 'HexenMap' / 'language.json'


@lru_cache(maxsize=1)
def get_language():
    """Keep one language for the lifetime of the current interface."""
    try:
        value = json.loads(language_path().read_text(encoding='utf-8-sig'))['language']
        return value if isinstance(value, str) and value in LANGUAGES else 'pt-BR'
    except (OSError, ValueError, KeyError, TypeError):
        return 'pt-BR'


def save_language(language):
    if language not in LANGUAGES:
        raise ValueError('Unsupported language')
    path = language_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix='language-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(handle, 'w', encoding='utf-8') as stream:
            json.dump({'language': language}, stream)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    # No cache invalidation: controls and workers apply the new language on restart.


@lru_cache(maxsize=1)
def english_messages():
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[2]))
    try:
        messages = json.loads((root / 'data/localization/ui-en-US.json').read_text(encoding='utf-8'))
        if isinstance(messages, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in messages.items()):
            return messages
    except (OSError, ValueError):
        pass
    return {}


def tr(message, *args, **kwargs):
    """Translate a presentation string, preserving format fields and unknown values."""
    if not isinstance(message, str):
        return message
    translated = english_messages().get(message, message) if get_language() == 'en-US' else message
    return translated.format(*args, **kwargs) if args or kwargs else translated
