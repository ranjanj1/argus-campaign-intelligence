from pathlib import Path

# Project root — two levels up from this file (argus/paths.py → argus/ → project root)
PROJECT_ROOT = Path(__file__).parent.parent

# Runtime data (created by Docker volumes, ignored by git)
LOCAL_DATA = PROJECT_ROOT / "local_data"

# Config files sit at project root
SETTINGS_YAML = PROJECT_ROOT / "settings.yaml"
SETTINGS_DIR = PROJECT_ROOT  # profile YAMLs live here too

# Prompt YAMLs
PROMPTS_DIR = PROJECT_ROOT / "argus" / "components" / "prompt_manager" / "prompts"
