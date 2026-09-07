from __future__ import annotations

import csv
import hashlib
import json
import re
import time
from collections import Counter
from contextlib import suppress
from pathlib import Path
from typing import Any

from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)

from .config import Settings
from .prompts import (
    FINAL_SYNTHESIS_PROMPT,
    INTERMEDIATE_SYNTHESIS_PROMPT,
    PAPER_INSTRUCTIONS,
    PAPER_PROMPT,
    SYNTHESIS_INSTRUCTIONS,
)
from .schemas import PAPER_SCHEMA


CANONICAL_CONCEPTS = {
    "distributieve rechtvaardigheid": "distributieve rechtvaardigheid",
    "verdelende rechtvaardigheid": "distributieve rechtvaardigheid",
    "distributional justice": "distributieve rechtvaardigheid",
    "distributive justice": "distributieve rechtvaardigheid",
    "procedurele rechtvaardigheid": "procedurele rechtvaardigheid",
    "procedural justice": "procedurele rechtvaardigheid",
    "erkennende rechtvaardigheid": "erkennende rechtvaardigheid",
    "erkenningsrechtvaardigheid": "erkennende rechtvaardigheid",
    "recognition justice": "erkennende rechtvaardigheid",
    "recognitional justice": "erkennende rechtvaardigheid",
    "herstellende rechtvaardigheid": "herstellende rechtvaardigheid",
    "restorative justice": "herstellende rechtvaardigheid",
    "kosmopolitische rechtvaardigheid": "kosmopolitische rechtvaardigheid",
    "cosmopolitan justice": "kosmopolitische rechtvaardigheid",
    "intergenerationele rechtvaardigheid": "intergenerationele rechtvaardigheid",
    "intergenerational justice": "intergenerationele rechtvaardigheid",
    "intergenerational equity": "intergenerationele rechtvaardigheid",
}


def discover_files(settings: Settings) -> list[Path]:
    pattern = "**/*" if settings.recursive else "*"
    return sorted(
        (
            p
            for p in settings.literature_dir.glob(pattern)
            if p.is_file() and p.suffix.lower() in settings.extensions
        ),
        key=lambda p: str(p).lower(),
    )


def safe_output_name(path: Path, root: Path) -> str:
    relative = str(path.relative_to(root))
    stem = re.sub(r"[^A-Za-z0-9À-ÿ._-]+", "_", path.stem).strip("_")[:100]
    digest = hashlib.sha1(relative.encode("utf-8")).hexdigest()[:10]
    return f"{stem or 'paper'}__{digest}.json"


def normalize_concept(label: str) -> str:
    cleaned = re.sub(r"\s+", " ", label.strip().lower()).strip(" .,:;")
    return CANONICAL_CONCEPTS.get(cleaned, cleaned)


def append_manifest(settings: Settings, record: dict[str, Any]) -> None:
    with settings.manifest_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def response_usage(response: Any) -> Any:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    if hasattr(usage, "model_dump"):
        return usage.model_dump()
    return str(usage)


def api_call_with_retry(client: OpenAI, settings: Settings, **kwargs: Any) -> Any:
    retryable = (
        RateLimitError,
        APIConnectionError,
        APITimeoutError,
        InternalServerError,
    )
    for attempt in range(1, settings.max_retries + 1):
        try:
            return client.responses.create(**kwargs)
        except retryable as exc:
            if attempt == settings.max_retries:
                raise
            wait_seconds = min(60, 2**attempt)
            print(
                f"  Tijdelijke API-fout ({type(exc).__name__}); "
                f"opnieuw proberen over {wait_seconds}s."
            )
            time.sleep(wait_seconds)
    raise RuntimeError("Onbereikbare retry-status")


def analyse_paper(
    client: OpenAI,
    settings: Settings,
    paper_path: Path,
    force: bool = False,
) -> Path:
    relative_path = paper_path.relative_to(settings.literature_dir)
    output_path = settings.papers_dir / safe_output_name(
        paper_path, settings.literature_dir
    )

    if output_path.exists() and settings.skip_existing and not force:
        print(f"SKIP     {relative_path}")
        return output_path

    print(f"ANALYSE  {relative_path}")
    uploaded_file_id: str | None = None

    try:
        with paper_path.open("rb") as handle:
            uploaded = client.files.create(file=handle, purpose="user_data")
        uploaded_file_id = uploaded.id

        response = api_call_with_retry(
            client,
            settings,
            model=settings.model,
            reasoning={"effort": settings.reasoning_effort},
            instructions=PAPER_INSTRUCTIONS,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_file", "file_id": uploaded_file_id},
                        {
                            "type": "input_text",
                            "text": (
                                f"Bronbestand: {relative_path}\n\n"
                                f"{PAPER_PROMPT}\n\n"
                                "Analyseer nu uitsluitend het aangeleverde bestand."
                            ),
                        },
                    ],
                }
            ],
            text={"format": PAPER_SCHEMA},
            max_output_tokens=30_000,
            store=False,
        )

        if getattr(response, "status", "completed") != "completed":
            raise RuntimeError(
                f"API-response niet voltooid: {getattr(response, 'status', None)}"
            )

        if not response.output_text:
            raise RuntimeError("API-response bevat geen output_text")

        result = json.loads(response.output_text)
        result["metadata"]["bronbestand"] = str(relative_path)

        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)

        append_manifest(
            settings,
            {
                "type": "paper",
                "bronbestand": str(relative_path),
                "output": str(output_path),
                "model": settings.model,
                "reasoning_effort": settings.reasoning_effort,
                "response_id": getattr(response, "id", None),
                "usage": response_usage(response),
                "status": "completed",
            },
        )
        return output_path

    except Exception as exc:
        append_manifest(
            settings,
            {
                "type": "paper",
                "bronbestand": str(relative_path),
                "status": "error",
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        raise

    finally:
        if uploaded_file_id:
            with suppress(Exception):
                client.files.delete(uploaded_file_id)


def load_paper_records(settings: Settings) -> list[tuple[Path, dict[str, Any]]]:
    records: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(settings.papers_dir.glob("*.json")):
        with path.open("r", encoding="utf-8") as handle:
            records.append((path, json.load(handle)))
    return records


def calculate_concept_frequencies(
    records: list[tuple[Path, dict[str, Any]]],
) -> Counter[str]:
    counts: Counter[str] = Counter()
    for _, record in records:
        labels = record.get("q3_rechtvaardigheidsconcepten", {}).get("labels", [])
        concepts_in_paper = {
            normalize_concept(label)
            for label in labels
            if isinstance(label, str) and label.strip()
        }
        counts.update(concepts_in_paper)
    return counts


def write_concept_frequencies(settings: Settings, counts: Counter[str]) -> None:
    with settings.concept_frequency_file.open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(["concept", "aantal_papers"])
        for concept, count in counts.most_common():
            writer.writerow([concept, count])


def concept_frequency_text(counts: Counter[str]) -> str:
    if not counts:
        return "Geen rechtvaardigheidsconcepten geregistreerd."
    lines = [
        "Frequentie = aantal afzonderlijke paperrecords waarin het concept minimaal eenmaal voorkomt:"
    ]
    lines.extend(f"- {concept}: {count}" for concept, count in counts.most_common())
    return "\n".join(lines)


def serialize_records(records: list[tuple[Path, dict[str, Any]]]) -> str:
    payload = [
        {
            "bronbestand": record.get("metadata", {}).get("bronbestand", "onbekend"),
            "paperrecord": record,
        }
        for _, record in records
    ]
    return json.dumps(payload, ensure_ascii=False, indent=2)


def split_records_by_chars(
    records: list[tuple[Path, dict[str, Any]]], max_chars: int
) -> list[list[tuple[Path, dict[str, Any]]]]:
    chunks: list[list[tuple[Path, dict[str, Any]]]] = []
    current: list[tuple[Path, dict[str, Any]]] = []
    current_size = 0

    for item in records:
        item_size = len(json.dumps(item[1], ensure_ascii=False))
        if current and current_size + item_size > max_chars:
            chunks.append(current)
            current = []
            current_size = 0
        current.append(item)
        current_size += item_size

    if current:
        chunks.append(current)
    return chunks


def create_intermediate_synthesis(
    client: OpenAI,
    settings: Settings,
    records: list[tuple[Path, dict[str, Any]]],
    part_number: int,
) -> str:
    response = api_call_with_retry(
        client,
        settings,
        model=settings.model,
        reasoning={"effort": settings.reasoning_effort},
        instructions=SYNTHESIS_INSTRUCTIONS,
        input=(
            f"{INTERMEDIATE_SYNTHESIS_PROMPT}\n\n"
            f"PAPERRECORDS:\n{serialize_records(records)}"
        ),
        max_output_tokens=30_000,
        store=False,
    )
    text = response.output_text
    if not text:
        raise RuntimeError("Lege tussensynthese ontvangen")

    output_path = settings.intermediate_dir / f"tussensynthese_{part_number:03d}.md"
    output_path.write_text(text, encoding="utf-8")
    append_manifest(
        settings,
        {
            "type": "intermediate_synthesis",
            "part": part_number,
            "n_papers": len(records),
            "model": settings.model,
            "reasoning_effort": settings.reasoning_effort,
            "response_id": getattr(response, "id", None),
            "usage": response_usage(response),
            "status": "completed",
        },
    )
    return text


def make_final_synthesis(
    client: OpenAI,
    settings: Settings,
    records: list[tuple[Path, dict[str, Any]]],
) -> str:
    if not records:
        raise RuntimeError("Geen paperrecords gevonden voor de synthese")

    counts = calculate_concept_frequencies(records)
    write_concept_frequencies(settings, counts)
    all_material = serialize_records(records)

    if len(all_material) <= settings.max_synthesis_input_chars:
        synthesis_material = "PAPER-VOOR-PAPER RECORDS:\n\n" + all_material
    else:
        chunks = split_records_by_chars(
            records, max_chars=settings.max_synthesis_input_chars
        )
        partials: list[str] = []
        print(
            f"Corpus te groot voor ingestelde grens; maak {len(chunks)} tussensyntheses."
        )
        for number, chunk in enumerate(chunks, start=1):
            print(f"TUSSEN   {number}/{len(chunks)} ({len(chunk)} papers)")
            partials.append(
                create_intermediate_synthesis(client, settings, chunk, number)
            )
        synthesis_material = (
            "TUSSENSYNTHESES (uitsluitend gebaseerd op paperrecords):\n\n"
            + "\n\n==============================\n\n".join(
                f"DEEL {number}\n{text}"
                for number, text in enumerate(partials, start=1)
            )
        )

    final_input = (
        f"{FINAL_SYNTHESIS_PROMPT}\n\n"
        f"AANTAL PAPERRECORDS: {len(records)}\n\n"
        "CONCEPTFREQUENTIES:\n"
        f"{concept_frequency_text(counts)}\n\n"
        "BRONMATERIAAL VOOR DEZE SYNTHESE:\n"
        f"{synthesis_material}"
    )

    print("SYNTHESE  eindsynthese")
    response = api_call_with_retry(
        client,
        settings,
        model=settings.model,
        reasoning={"effort": settings.reasoning_effort},
        instructions=SYNTHESIS_INSTRUCTIONS,
        input=final_input,
        max_output_tokens=50_000,
        store=False,
    )
    text = response.output_text
    if not text:
        raise RuntimeError("Lege eindsynthese ontvangen")

    settings.synthesis_file.write_text(text, encoding="utf-8")
    append_manifest(
        settings,
        {
            "type": "final_synthesis",
            "n_papers": len(records),
            "model": settings.model,
            "reasoning_effort": settings.reasoning_effort,
            "response_id": getattr(response, "id", None),
            "usage": response_usage(response),
            "output": str(settings.synthesis_file),
            "status": "completed",
        },
    )
    return text


def run_pipeline(
    settings: Settings,
    *,
    force: bool = False,
    papers_only: bool = False,
    synthesis_only: bool = False,
    limit: int | None = None,
) -> None:
    client = OpenAI(api_key=settings.api_key)

    if not synthesis_only:
        files = discover_files(settings)
        if limit is not None:
            files = files[:limit]
        if not files:
            raise SystemExit(
                f"Geen bestanden gevonden met extensies {sorted(settings.extensions)} "
                f"in {settings.literature_dir}"
            )

        print(f"{len(files)} bestand(en) geselecteerd.")
        successful = 0
        failed = 0
        for index, paper in enumerate(files, start=1):
            print(f"[{index}/{len(files)}]", end=" ")
            try:
                analyse_paper(client, settings, paper, force=force)
                successful += 1
            except Exception as exc:
                failed += 1
                print(f"FOUT     {paper.name}: {type(exc).__name__}: {exc}")
        print(f"Paperfase: {successful} succesvol, {failed} fout(en).")

    if papers_only:
        return

    records = load_paper_records(settings)
    if not records:
        raise SystemExit(f"Geen JSON-records gevonden in {settings.papers_dir}")
    print(f"Synthese op basis van {len(records)} paperrecord(s).")
    make_final_synthesis(client, settings, records)
