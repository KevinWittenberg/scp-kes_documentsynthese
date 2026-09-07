from pathlib import Path

from scp_kes_documentsynthese.pipeline import (
    normalize_concept,
    safe_output_name,
    split_records_by_chars,
)


def test_normalize_known_concept_synonyms() -> None:
    assert normalize_concept("Distributive Justice") == "distributieve rechtvaardigheid"
    assert normalize_concept("verdelende rechtvaardigheid") == "distributieve rechtvaardigheid"
    assert normalize_concept("Recognition Justice") == "erkennende rechtvaardigheid"


def test_normalize_unknown_concept_is_preserved_lowercase() -> None:
    assert normalize_concept("  Spatial Justice  ") == "spatial justice"


def test_safe_output_name_is_stable_and_path_sensitive() -> None:
    root = Path("/literatuur")
    first = root / "map_a" / "Paper 2026.pdf"
    second = root / "map_b" / "Paper 2026.pdf"

    assert safe_output_name(first, root) == safe_output_name(first, root)
    assert safe_output_name(first, root) != safe_output_name(second, root)
    assert safe_output_name(first, root).endswith(".json")


def test_split_records_keeps_all_records() -> None:
    records = [
        (Path("a.json"), {"x": "a" * 30}),
        (Path("b.json"), {"x": "b" * 30}),
        (Path("c.json"), {"x": "c" * 30}),
    ]
    chunks = split_records_by_chars(records, max_chars=50)
    flattened = [item for chunk in chunks for item in chunk]

    assert flattened == records
    assert len(chunks) >= 2
