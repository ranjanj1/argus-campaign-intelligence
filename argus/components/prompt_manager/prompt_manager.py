from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import yaml
from injector import inject, singleton

from argus.utils.skills import ClientSkill

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"


@singleton
class PromptManager:
    """
    Loads per-skill system prompts from YAML files at startup.

    Prompt files live in argus/components/prompt_manager/prompts/<skill>.yaml
    and must contain a top-level `system_prompt` key.

    Usage:
        prompt = prompt_manager.get(ClientSkill.SINGLE_CLIENT, client_id="acme_corp")
    """

    @inject
    def __init__(self) -> None:
        self._prompts: dict[str, str] = {}
        self._load(PROMPTS_DIR)

    def _load(self, directory: Path) -> None:
        for path in directory.glob("*.yaml"):
            try:
                data = yaml.safe_load(path.read_text())
                self._prompts[path.stem] = data["system_prompt"]
                logger.debug("Loaded prompt: %s", path.stem)
            except Exception as exc:
                logger.warning("Failed to load prompt %s: %s", path.name, exc)
        logger.info("PromptManager loaded %d prompts: %s",
                    len(self._prompts), list(self._prompts.keys()))

    def get(
        self,
        skill: ClientSkill | str,
        client_id: str = "",
        today: str | None = None,
    ) -> str:
        """
        Return the system prompt for the given skill.

        Args:
            skill:      ClientSkill enum value or raw string.
            client_id:  Injected into prompts that reference {client_id}.
            today:      Override today's date string (defaults to real date).

        Falls back to `all_campaigns` prompt if the skill has no dedicated file.
        """
        key = skill.value if isinstance(skill, ClientSkill) else skill
        template = self._prompts.get(key) or self._prompts.get("all_campaigns", "")

        return template.format(
            today=today or date.today().isoformat(),
            client_id=client_id,
        )

    def list_skills(self) -> list[str]:
        """Return the names of all loaded prompt files."""
        return list(self._prompts.keys())
