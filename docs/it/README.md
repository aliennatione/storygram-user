# Guida a Storygram

Storygram è un archivio locale basato su file. I record canonici sono file JSON in `data/`. Le modifiche proposte vengono revisionate prima di diventare canoniche.

## Requisiti

- Python 3.12+
- Git per il flusso predefinito con commit all'approvazione
- Opzionali: Docker, Ollama locale, Node Playwright per i test browser

## Installazione

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

È supportato anche il pacchetto wheel. Imposta `STORYGRAM_SCHEMA_DIR` se il pacchetto installato non trova `schema/`.

## Creare e validare un archivio

```bash
storygram init ./archive
storygram validate ./archive
storygram list --archive ./archive
```

`init` crea tutte le directory canoniche e copia i 15 schemi. Non inizializza Git; esegui `git init ./archive` se vuoi il commit all'approvazione.

## Revisionare una proposta

```bash
storygram proposal new --file proposta.json --archive ./archive
storygram proposal show proposal:example-1 --archive ./archive
storygram proposal approve proposal:example-1 --archive ./archive --dry-run
storygram proposal approve proposal:example-1 --archive ./archive
```

La UI web usa lo stesso motore, inclusa una pagina **Records** in sola lettura con filtri per tipo/stato/visibilità/testo e download di export JSON/JSON-LD/YAML/Markdown per il filtro corrente, dettaglio con JSON grezzo e link a riferimenti e backlink, un modulo **Aggiungi memoria** che crea proposte Episode in attesa, moduli **Aggiungi fonte**, **Aggiungi entità** (ora inclusa Collection), **Aggiungi persona**, **Aggiungi relazione**, **Aggiungi asserzione**, **Aggiungi annotazione**, **Aggiungi narrazione** e **Aggiungi conflitto** che creano record di evidenza o proposte in attesa supportate da evidenza, una vista **Conflitti** in sola lettura che unisce i record Conflict espliciti con le contraddizioni derivate dalle asserzioni dietro un filtro per stato, una pagina **Media** in sola lettura per le voci del manifest checksummato, collegamenti incrociati tra record e proposte, una pagina **Generate** per modelli locali/Ollama o compatibili OpenAI e un link di modifica per le proposte pendenti. L'header cambia l'interfaccia tra inglese e italiano:

```bash
storygram web --archive ./archive --host 0.0.0.0 --port 8080
```

La UI non ha autenticazione ed è pensata per una rete locale controllata o un mapping di porta del container. È renderizzata lato server, funziona senza JavaScript ed è testata su Chromium e Firefox.

La pagina **Timeline** costruisce timeline a livello archivio o per entità, luogo e collezione dalle asserzioni aperte e collega ogni voce alla sua asserzione, ai record e alle evidenze. La pagina **Genogram** è una vista relazionale sperimentale in sola lettura con badge per i predicati supportati, warning e intervalli temporali rappresentativi più quelli aggregati. Nessuna delle due espone route di scrittura.

## Regole delle proposte

- Le operazioni sono `create`, `update_metadata`, `supersede` e `archive`.
- Le modifiche semantiche richiedono evidenza da Episode, Source o Annotation.
- I metadati usano un allowlist per tipo; i fatti vanno nelle Assertion.
- Un'Assertion superseded chiude `transaction_time.recorded_until`; il sostituto porta `supersedes`.
- I potenziali conflitti tra asserzioni bloccano l'apply finché un Conflict esplicito contiene entrambi gli ID.
- Le proposte applicate sono archiviate con stato `merged`; quelle pendenti restano locali e ignorate.
- L'approvazione è atomica, con rollback in caso di errore di scrittura o commit.

Il contratto completo è in `PROPOSAL_CONTRACT.md` in questa directory.

## API JSON

Gli agenti esterni possono creare, elencare, leggere, modificare, generare, rifiutare e ritirare proposte pendenti via HTTP. Non possono approvarle. Vedi [API.md](API.md).

```bash
curl -X POST http://localhost:8080/api/proposals \
  -H 'Content-Type: application/json' \
  --data @proposta.json
```

## Generazione LLM opzionale

```bash
ollama serve
ollama pull llama3.2
storygram proposal generate --text "Un ricordo..." --model llama3.2 --archive ./archive
```

Per un server compatibile OpenAI:

```bash
export STORYGRAM_LLM_PROVIDER=openai
export STORYGRAM_LLM_URL=http://127.0.0.1:8080
export STORYGRAM_LLM_MODEL=qwen3-4b
export STORYGRAM_LLM_API_KEY=...
storygram proposal generate --text "Un ricordo..." --archive ./archive
```

L'adapter forza `status=proposed`, scarta i campi sconosciuti e salva solo in `proposals/`. Non può approvare, applicare o modificare record canonici. Usa `--no-save` per controllare senza scrivere. La pagina **Generate** della UI usa lo stesso adapter; gli errori del provider vengono mostrati senza scrivere nulla. Regola la generazione con `$STORYGRAM_LLM_TIMEOUT` e `$STORYGRAM_LLM_MAX_TOKENS`.

Per il percorso GGUF locale incluso:

```bash
scripts/download-model.sh
STORYGRAM_MODELS_DIR=<host-path>/models scripts/llm-up.sh
```

Gli helper tengono il modello fuori da Git e lo montano in sola lettura nel profilo Compose opzionale `llm`. Il file 1.5B predefinito serve a verificare il cablaggio; su un container con 1 CPU il file 3B non è praticabile. Usa un solo endpoint compatibile OpenAI `qwen3-4b` come riferimento di qualità e fai sempre il dry-run delle proposte generate.

## Comandi legacy e derivati

Questi comandi sono deterministici e offline, ma alcuni restano più limitati di `PRD.md`:

- `storygram ingest episode FILE [--archive PATH] [--overwrite]` copia una cattura solo in `inbox/` e scrive un sidecar con checksum in `inbox/.storygram/<filename>.json` (`format` `storygram.capture/1`, dimensione, MIME type, SHA-256, `ingested_at`, `overwritten`). Non scrive mai in `data/` e rifiuta le sovrascritture silenziose; `--json` stampa i metadati della cattura.
- `storygram export [--format json|jsonld|yaml|markdown] [--visibility VALUE ...] [--archive PATH]` legge i record canonici dal registry, ordina per ID e fallisce su JSON malformato. Con un filtro di visibilità, i record senza `visibility` sono esclusi. `jsonld` resta una proiezione locale `@id`/`@type`, non un'espansione RDF completa. JSON, JSON-LD e YAML fanno round-trip senza perdita (JSON resta la lista nativa); Markdown usa front matter YAML più un corpo renderizzato, quindi il front matter è la fonte di verità e le modifiche solo al corpo non vengono re-importate. Non esiste un import canonico diretto: `storygram import` produce una proposta pendente, quindi revisione e approvazione passano ancora dalle proposte.
- `storygram import FILE [--format json|jsonld|yaml|markdown] [--evidence ID ...] [--id PROPOSAL_ID] [--archive PATH]` legge un export e crea una proposta pendente di soli `create`. Valida lo schema di ogni record ed esegue lo stesso planner del dry-run di approvazione prima di scrivere. I record Episode/Source/Annotation importati diventano evidenza per le operazioni successive; `--evidence` può puntare a catture già canoniche. L'import non scrive mai in `data/`: revisione e approvazione restano umane.
- `storygram media add FILE [--uri URI] [--visibility VALORE] [--acquired-at TS] [--notes TESTO] [--name ETICHETTA] [--overwrite] [--archive PATH]` registra un file media esterno in `media-manifest/` con URI, checksum SHA-256, tipo MIME, dimensioni, visibilità e metadati di acquisizione; il file media non viene mai copiato né committato, le voci sono indirizzate per contenuto e le sovrascritture silenziose sono rifiutate. `storygram media list [--json]` elenca le voci registrate.
- `storygram rebuild [PATH]` ricostruisce solo l'indice di ricerca SQLite/FTS5. È idempotente, rimuove i record obsoleti e segnala gli input malformati.
- `storygram search QUERY [--archive PATH] [--rebuild]` cerca prima ID e tipi esatti, poi nel contenuto indicizzato. L'indice si aggiorna quando cambiano i file canonici.
- `storygram conflicts [--status VALUE] [--archive PATH]` unisce i Conflict espliciti con le contraddizioni derivate dalle asserzioni, deduplica le coppie e mostra entrambe le asserzioni con l'evidenza.
- `storygram timeline [ID] [--all] [--archive PATH]` esclude le asserzioni superseded, archived e rejected, ordina per inizio del valid-time e include i campi di evidenza. `ID` copre timeline di entità, luoghi e collezioni; una collezione include anche le asserzioni sui record che dichiarano `relation:member_of` verso di essa. `--all` costruisce una timeline a livello archivio.
- `storygram genogram ID [--archive PATH]` è sperimentale: legge le asserzioni `relation:*` e i record Relationship con estremi espliciti, segnala i predicati non supportati, avvisa sui record Relationship privi di estremi completi e deduplica le triple Assertion/Relationship equivalenti (preferendo la Relationship registrata più di recente), elencando ogni ID contribuente in `related_ids`, ed espone i dati temporali come `valid_time`/`transaction_time` del rappresentante più `valid_times`/`transaction_times` aggregati.

`validate`, `get`, `list` e `git-check` restano la superficie stabile di lettura e validazione.

## Test

```bash
PYTHONPATH=/data/src python -m pytest -q
ruff check src tests
ruff format --check src tests
mypy src
npm run test:e2e
npm run test:e2e:firefox
```

`npm run test:e2e` avvia il server locale reale e lo guida con Playwright e Chromium di sistema. `npm run test:e2e:firefox` guida lo stesso server tramite WebDriver/geckodriver con Firefox di sistema. Python Playwright non è utilizzabile su Alpine musl; lì il percorso supportato è Node Playwright. `npm run test:e2e:all` esegue entrambi.

## Container

Sono inclusi `Dockerfile` e `compose.yaml`. L'immagine è stata verificata end-to-end tramite un daemon host compatibile Docker (Podman Engine 5.8.2 via Docker CLI): avvio non-root, auto-init, healthcheck, applicazione di una proposta nel container, persistenza dopo restart/ricreazione e bind mount host sono tutti passati.

```bash
STORYGRAM_PORT=18080 docker compose -p storygram-test up --build -d
docker compose -p storygram-test ps
docker compose -p storygram-test --profile ollama up -d
docker compose -p storygram-test exec ollama ollama pull llama3.2
```

Il container predefinito inizializza automaticamente `/data` e Git quando serve, gira come utente non-root `storygram` (UID/GID 100:101) e persiste i dati in un volume nominato. Per un bind mount, assegna alla directory host quell'UID/GID; scoprili con `docker run --rm --entrypoint id storygram:local`. Imposta `STORYGRAM_AUTO_INIT=0` per disattivare. Il profilo Ollama è opzionale; il nucleo deterministico e la UI funzionano senza. Usa un nome progetto e una porta unici per i test e rimuovi solo le risorse create.

## Demo

Materiale derivato e ignorato da Git in `generated/demos/`; non tocca mai i dati canonici.

Animazioni Manim (dati sintetici):

- `generated/demos/manim/media/videos/storygram_timeline/480p15/StorygramTimeline.mp4`
- `generated/demos/manim/media/videos/storygram_proposal_flow/480p15/StorygramProposalFlow.mp4`

Riproducile con qualsiasi player. Per ri-renderizzare:

```bash
PYTHONPATH=/data/src python scripts/demo_tools.py render manim generated/demos/manim/storygram_timeline.py
PYTHONPATH=/data/src python scripts/demo_tools.py render manim generated/demos/manim/storygram_proposal_flow.py
```

Corso Slidev di introduzione (bilingue):

- Sito generato: `generated/demos/vcr/storygram_intro/en/dist/index.html` e `.../it/dist/index.html`.
- Server di sviluppo: `cd generated/demos/vcr/storygram_intro && slidev en/index.md`.
- Per rigenerare: `cd generated/demos/vcr/storygram_intro && slidev build en/index.md --out dist`.
