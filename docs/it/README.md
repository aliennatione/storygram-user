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

La UI web usa lo stesso motore, inclusa una pagina **Generate** per modelli locali/Ollama o compatibili OpenAI e un link di modifica per le proposte pendenti:

```bash
storygram web --archive ./archive --host 0.0.0.0 --port 8080
```

La UI non ha autenticazione ed è pensata per una rete locale controllata o un mapping di porta del container.

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

- `storygram ingest episode FILE [--archive PATH] [--overwrite]` copia una cattura solo in `inbox/`. Non scrive mai in `data/` e rifiuta le sovrascritture silenziose.
- `storygram export [--format json|jsonld] [--visibility VALUE ...] [--archive PATH]` legge i record canonici dal registry, ordina per ID e fallisce su JSON malformato. Con un filtro di visibilità, i record senza `visibility` sono esclusi. `jsonld` è una proiezione minima `@id`/`@type`, non un round-trip RDF completo.
- `storygram rebuild [PATH]` ricostruisce solo l'indice di ricerca SQLite/FTS5. È idempotente, rimuove i record obsoleti e segnala gli input malformati.
- `storygram search QUERY [--archive PATH] [--rebuild]` cerca prima ID e tipi esatti, poi nel contenuto indicizzato. L'indice si aggiorna quando cambiano i file canonici.
- `storygram conflicts [--status VALUE] [--archive PATH]` unisce i Conflict espliciti con le contraddizioni derivate dalle asserzioni, deduplica le coppie e mostra entrambe le asserzioni con l'evidenza.
- `storygram timeline ID [--archive PATH]` esclude le asserzioni superseded, archived e rejected, ordina per inizio del valid-time e include i campi di evidenza.
- `storygram genogram ID [--archive PATH]` è sperimentale: usa le asserzioni `relation:*`, segnala i predicati non supportati e ignora i record Relationship finché lo schema non modella i loro estremi.

`validate`, `get`, `list` e `git-check` restano la superficie stabile di lettura e validazione.

## Test

```bash
PYTHONPATH=/data/src python -m pytest -q
ruff check src tests
ruff format --check src tests
mypy src
npm run test:e2e
```

`npm run test:e2e` avvia il server locale reale e lo guida con Playwright e Chromium di sistema. Python Playwright non è utilizzabile su Alpine musl; lì il percorso supportato è Node Playwright.

## Container

Sono inclusi `Dockerfile` e `compose.yaml`. L'immagine è stata verificata end-to-end tramite un daemon host compatibile Docker (Podman Engine 5.8.2 via Docker CLI): avvio non-root, auto-init, healthcheck, applicazione di una proposta nel container, persistenza dopo restart/ricreazione e bind mount host sono tutti passati.

```bash
STORYGRAM_PORT=18080 docker compose -p storygram-test up --build -d
docker compose -p storygram-test ps
docker compose -p storygram-test --profile ollama up -d
docker compose -p storygram-test exec ollama ollama pull llama3.2
```

Il container predefinito inizializza automaticamente `/data` e Git quando serve, gira come utente non-root `storygram` (UID/GID 100:101) e persiste i dati in un volume nominato. Per un bind mount, assegna alla directory host quell'UID/GID; scoprili con `docker run --rm --entrypoint id storygram:local`. Imposta `STORYGRAM_AUTO_INIT=0` per disattivare. Il profilo Ollama è opzionale; il nucleo deterministico e la UI funzionano senza. Usa un nome progetto e una porta unici per i test e rimuovi solo le risorse create.
