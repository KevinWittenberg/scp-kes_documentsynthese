# SCP KES documentsynthese

Reproduceerbare LLM-pipeline voor de literatuursynthese over rechtvaardigheid in klimaat- en energiebeleid.

De workflow bestaat uit twee strikt gescheiden stappen:

1. **Paper-voor-paper extractie**: iedere publicatie wordt afzonderlijk door `gpt-5.6-terra` met reasoning effort `medium` geanalyseerd en als gestructureerd JSON-record opgeslagen. Als een paper een deelvraag niet behandelt, wordt exact `"geen informatie"` opgeslagen.
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

Vul daarna alleen je eigen `OPENAI_API_KEY` in `.env` in. Het Open OnDemand-pad naar de literatuur staat al ingevuld.

## Configuratie

De relevante `.env`-instellingen zijn:

```dotenv
OPENAI_API_KEY=sk-vul-hier-je-key-in
OPENAI_MODEL=gpt-5.6-terra
OPENAI_REASONING_EFFORT=medium

LITERATURE_DIR="/scp/J/project/De sociaal-maatschappelijke dimensie van klimaat- en energiebeleid - 20260105/literatuur/Wetenschappelijke publicaties/01_Rechtvaardigheid"

OUTPUT_DIR="./outputs"
FILE_EXTENSIONS=".pdf"
RECURSIVE=true
SKIP_EXISTING=true
MAX_SYNTHESIS_INPUT_CHARS=1500000
```

`.env` staat in `.gitignore` en hoort **nooit** in Git te worden gecommit.

## Eerst veilig controleren

Voordat je API-kosten maakt, controleer welke bestanden het script ziet:

```bash
python run.py --dry-run
```

`--dry-run` doet geen API-call en vereist geen API-key.

Test daarna bij voorkeur eerst één paper:

```bash
python run.py --papers-only --limit 1
```

Bekijk vervolgens het JSON-bestand in `outputs/papers/`. Als dat er inhoudelijk goed uitziet, kun je het corpus verwerken.

## Hele pipeline uitvoeren

```bash
python run.py
```

De pipeline is hervatbaar. Bestaande paperoutputs worden standaard overgeslagen. Als een run halverwege stopt, kun je hetzelfde commando opnieuw uitvoeren zonder reeds afgeronde papers opnieuw te laten analyseren.

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

```bash
python run.py --papers-only --limit 3
```

## Output

Na een volledige run ontstaat onder `outputs/`:

```text
outputs/
├── papers/
│   ├── <papernaam>__<hash>.json
│   ├── <papernaam>__<hash>.json
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
- De paperfase doet **extractie op studieniveau** en vraagt een paper dus niet om corpusbrede conclusies te trekken.
- Eén paper bepaalt niet welke rechtvaardigheidsconcepten in de hele literatuur het meest gebruikt zijn.
- De frequenties van rechtvaardigheidsconcepten worden na de paperfase programmatisch berekend als **het aantal afzonderlijke papers waarin een concept voorkomt**, niet als woordfrequentie.
- Evidente synoniemen, zoals `distributive justice` en `verdelende rechtvaardigheid`, worden voor deze telling gestandaardiseerd.
- De prompts instrueren het model om eigen empirische bevindingen, door auteurs aangehaalde eerdere literatuur en theoretische/normatieve argumenten niet ongemerkt gelijk te behandelen.
- Causale conclusies mogen niet uitsluitend uit correlaties worden afgeleid.
- Een grootste/belangrijkste bron van onvrede mag alleen worden genoemd als de onderliggende evidence werkelijk een vergelijking ondersteunt.
- De eindsynthese gebruikt uitsluitend de opgeslagen paperrecords.
- Bij een zeer groot corpus maakt de pipeline eerst compacte tussensyntheses uit subsets van de paperrecords en combineert deze daarna in de eindsynthese.

## Bestandsinput

De huidige configuratie doorzoekt `.pdf`-bestanden recursief. Als er later ook bijvoorbeeld `.docx`-bestanden in dezelfde map moeten worden meegenomen, verander dan in `.env`:

```dotenv
FILE_EXTENSIONS=".pdf,.docx"
```

## Tests

```bash
pytest
```

De tests doen geen API-calls. Ze controleren onder andere conceptnormalisatie, stabiele outputnamen en het opsplitsen van grote corpora.

## Aanbevolen eerste run

```bash
cp .env.example .env
# vul OPENAI_API_KEY in .env in
python run.py --dry-run
python run.py --papers-only --limit 1
```

Controleer daarna eerst handmatig het gegenereerde paperrecord voordat je `python run.py` over het volledige corpus laat lopen.
