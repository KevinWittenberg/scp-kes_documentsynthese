from __future__ import annotations

import argparse

from scp_kes_documentsynthese.config import load_settings
from scp_kes_documentsynthese.pipeline import discover_files, run_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Paper-voor-paper extractie en corpusbrede synthese van klimaat- en energierechtvaardigheidsliteratuur."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Toon welke bestanden worden gevonden zonder API-key of API-calls.",
    )
    parser.add_argument(
        "--papers-only",
        action="store_true",
        help="Voer alleen de paper-voor-paper analyse uit.",
    )
    parser.add_argument(
        "--synthesis-only",
        action="store_true",
        help="Maak alleen de synthese uit reeds opgeslagen paperrecords.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Analyseer papers opnieuw, ook als er al een JSON-output bestaat.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Verwerk maximaal N gevonden papers; handig voor een test-run.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.papers_only and args.synthesis_only:
        raise SystemExit("Gebruik niet tegelijk --papers-only en --synthesis-only.")
    if args.limit is not None and args.limit < 1:
        raise SystemExit("--limit moet minimaal 1 zijn.")
    if args.synthesis_only and args.limit is not None:
        raise SystemExit("--limit heeft geen betekenis bij --synthesis-only.")

    settings = load_settings(require_api_key=not args.dry_run)

    print(f"Model:       {settings.model}")
    print(f"Reasoning:   {settings.reasoning_effort}")
    print(f"Literatuur:  {settings.literature_dir}")
    print(f"Output:      {settings.output_dir}")
    print(f"Extensies:   {', '.join(sorted(settings.extensions))}")
    print(f"Recursief:   {settings.recursive}")

    if args.dry_run:
        files = discover_files(settings)
        if args.limit is not None:
            files = files[: args.limit]
        print(f"\n{len(files)} bestand(en) geselecteerd:\n")
        for index, path in enumerate(files, start=1):
            print(f"{index:>4}. {path.relative_to(settings.literature_dir)}")
        return

    run_pipeline(
        settings,
        force=args.force,
        papers_only=args.papers_only,
        synthesis_only=args.synthesis_only,
        limit=args.limit,
    )

    print("\nKlaar.")
    print(f"Paperrecords:       {settings.papers_dir}")
    print(f"Conceptfrequenties: {settings.concept_frequency_file}")
    print(f"Synthese:           {settings.synthesis_file}")
    print(f"Manifest:           {settings.manifest_file}")


if __name__ == "__main__":
    main()
