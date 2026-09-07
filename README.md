# SCP KES documentsynthese

Reproduceerbare LLM-pipeline voor de literatuursynthese over rechtvaardigheid in klimaat- en energiebeleid.

De workflow bestaat uit twee strikt gescheiden stappen:

1. **Paper-voor-paper extractie**: iedere publicatie wordt afzonderlijk door `gpt-5.6-terra` (reasoning effort `medium`) geanalyseerd en als gestructureerd JSON-record opgeslagen. Als een paper een deelvraag niet behandelt, wordt exact `"geen informatie"` opgeslagen.
2. **Corpusbrede synthese**: de uiteindelijke synthese wordt uitsluitend gemaakt op basis van de opgeslagen paperrecords, niet opnieuw rechtstreeks uit de oorspronkelijke papers.

## Projectstructuur

```text
scp-kes_documentsynthese/
├── .env.example
├── .gitignore
├── README.md
├── pyproject.toml
├── requirements.txt
├── run.py
├── src/
│   └── scp_kes_documentsynthese/
│       ├── __init__.py
│       ├── config.py
│       ├── pipeline.py
│       ├── prompts.py
│       └── schemas.py
├── tests/
│   └── test_core.py
└── outputs/
    └── .gitkeep
```

## Installatie op Linux / Open OnDemand

```bash
git clone https://github.com/KevinWittenberg/scp-kes_documentsynthese.git
cd scp-kes_documentsynthese

python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

cp .env.example .env
```

Vul daarna in `.env` je API-key en het **Linux-pad** naar de literatuurmap in.

> Het oorspronkelijke pad `J:\\project\\...` is een Windows-pad. In Open OnDemand moet `LITERATURE_DIR` verwijzen naar de Linux-mount van dezelfde projectshare, bijvoorbeeld `/project/...`, `/mnt/...` of een instellingsspecifiek mountpad.

## Configuratie

Voorbeeld `.env`:

```dotenv
OPENAI_API_KEY=sk-vul-hier-je-key-in
OPENAI_MODEL=gpt-5.6-terra
OPENAI_REASONING_EFFORT=medium

LITERATURE_DIR="/VUL/HIER/HET/LINUX/PAD/NAAR/01_Rechtvaardigheid"
OUTPUT_DIR="./outputs"
FILE_EXTENSIONS=".pdf"
RECURSIVE=true
SKIP_EXISTING=true
MAX_SYNTHESIS_INPUT_CHARS=1500000
```

`.env` staat in `.gitignore` en hoort **nooit** in Git te worden gecommit.

## Eerst controleren welke bestanden worden gevonden

Voordat je API-kosten maakt:

```bash
python run.py --dry-run
```

Of test eerst met één paper:

```bash
python run.py --papers-only --limit 1
```

## Hele pipeline uitvoeren

```bash
python run.py
```

De pipeline is hervatbaar. Bestaande paperoutputs worden standaard overgeslagen. Als een run halverwege stopt, kun je hetzelfde commando dus opnieuw uitvoeren.

### Alleen paperanalyses

```bash
python run.py --papers-only
```

### Alleen synthese uit bestaande paperrecords

```bash
python run.py --synthesis-only
```

### Alles opnieuw analyseren

```bash
python run.py --force
```

### Beperkt aantal papers verwerken

Handig voor een eerste test:

```bash
python run.py --limit 3
```

## Output

Na een run ontstaat onder `outputs/`:

```text
outputs/
├── papers/
│   ├── paper_1__<hash>.json
│   ├── paper_2__<hash>.json
│   └── ...
├── intermediate/
│   └── tussensynthese_*.md      # alleen bij een zeer groot corpus
├── concept_frequencies.csv
├── manifest.jsonl
└── synthesis.md
```

`manifest.jsonl` registreert per API-call onder andere het bronbestand, model, response-id, tokengebruik en eventuele fouten.

## Methodologische keuzes

- Een individuele paper hoeft niet alle onderzoeksvragen te beantwoorden.
- Ontbrekende informatie wordt op het niveau van de afzonderlijke deelvraag als exact `"geen informatie"` vastgelegd.
- Eén paper mag niet zelfstandig corpusbrede uitspraken doen over bijvoorbeeld "de meest gebruikte" rechtvaardigheidsconcepten.
- De zes meest gebruikte concepten worden pas na alle paperanalyses bepaald op basis van **het aantal papers waarin een concept voorkomt**; niet op basis van woordfrequentie.
- De prompts instrueren het model om empirische eigen bevindingen, aangehaalde eerdere literatuur en theoretische/normatieve argumenten niet ongemerkt gelijk te behandelen.
- Causale uitspraken mogen niet uit correlaties worden afgeleid.
- De eindsynthese gebruikt uitsluitend de opgeslagen paperrecords.
- Bij een zeer groot corpus maakt de pipeline eerst compacte tussensyntheses en gebruikt die vervolgens als input voor de eindsynthese.

## Tests

```bash
pytest
```

De tests doen geen API-calls en controleren enkele kernfuncties, waaronder conceptnormalisatie en consistente outputnamen.
