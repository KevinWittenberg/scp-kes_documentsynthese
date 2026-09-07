from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "ja", "on"}


@dataclass(frozen=True)
class Settings:
    api_key: str
    model: str
    reasoning_effort: str
    literature_dir: Path
    output_dir: Path
    recursive: bool
    skip_existing: bool
    extensions: frozenset[str]
    max_synthesis_input_chars: int
    max_retries: int = 5

    @property
    def papers_dir(self) -> Path:
        return self.output_dir / "papers"

    @property
    def intermediate_dir(self) -> Path:
        return self.output_dir / "intermediate"

    @property
    def synthesis_file(self) -> Path:
        return self.output_dir / "synthesis.md"

    @property
    def concept_frequency_file(self) -> Path:
        return self.output_dir / "concept_frequencies.csv"

    @property
    def manifest_file(self) -> Path:
        return self.output_dir / "manifest.jsonl"


def load_settings(require_api_key: bool = True) -> Settings:
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if require_api_key and not api_key:
        raise SystemExit(
            "OPENAI_API_KEY ontbreekt. Kopieer .env.example naar .env en vul je API-key in."
        )

    raw_literature_dir = os.getenv("LITERATURE_DIR", "").strip()
    if not raw_literature_dir:
        raise SystemExit("LITERATURE_DIR ontbreekt in .env.")

    if re.match(r"^[A-Za-z]:[\\/]", raw_literature_dir):
        raise SystemExit(
            "LITERATURE_DIR is een Windows-pad. Dit script draait op Linux/Open OnDemand; "
            "gebruik het Linux-mountpad van dezelfde projectshare."
        )

    literature_dir = Path(raw_literature_dir).expanduser()
    if not literature_dir.exists():
        raise SystemExit(f"Literatuurmap bestaat niet: {literature_dir}")
    if not literature_dir.is_dir():
        raise SystemExit(f"LITERATURE_DIR is geen map: {literature_dir}")

    raw_extensions = os.getenv("FILE_EXTENSIONS", ".pdf")
    extensions = frozenset(
        ext.strip().lower() if ext.strip().startswith(".") else f".{ext.strip().lower()}"
        for ext in raw_extensions.split(",")
        if ext.strip()
    )

    settings = Settings(
        api_key=api_key,
        model=os.getenv("OPENAI_MODEL", "gpt-5.6-terra").strip(),
        reasoning_effort=os.getenv("OPENAI_REASONING_EFFORT", "medium").strip(),
        literature_dir=literature_dir,
        output_dir=Path(os.getenv("OUTPUT_DIR", "./outputs")).expanduser(),
        recursive=_as_bool(os.getenv("RECURSIVE"), True),
        skip_existing=_as_bool(os.getenv("SKIP_EXISTING"), True),
        extensions=extensions,
        max_synthesis_input_chars=int(
            os.getenv("MAX_SYNTHESIS_INPUT_CHARS", "1500000")
        ),
    )

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    settings.papers_dir.mkdir(parents=True, exist_ok=True)
    settings.intermediate_dir.mkdir(parents=True, exist_ok=True)
    return settings
