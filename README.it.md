# Storygram

Archivio locale e versionabile per storie di vita: episodi, fonti, persone, luoghi, eventi, relazioni, asserzioni, conflitti e narrazioni. Il nucleo è deterministico e funziona offline senza LLM.

## Avvio rapido

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"

storygram init ./archive
git init ./archive
storygram validate ./archive
storygram web --archive ./archive --host 0.0.0.0 --port 8080
```

Apri `http://localhost:8080`, incolla o genera una proposta e controlla il dry-run prima di approvare. L'approvazione è l'unico percorso verso `data/`.

## Flusso delle proposte

Le proposte pendenti restano in `proposals/` e sono ignorate da Git. Le proposte approvate vengono archiviate in `data/proposals/` e committate.

```bash
storygram proposal new --file proposal.json
storygram proposal list
storygram proposal show proposal:example-1
storygram proposal approve proposal:example-1 --dry-run
storygram proposal approve proposal:example-1
storygram proposal reject proposal:example-1 --reason "manca evidenza"
storygram proposal withdraw proposal:example-1 --reason "sorgente errata"
```

`approve` scrive in modo atomico e crea un commit Git limitato ai file applicati. Usa `--no-commit` per saltare Git. L'archivio deve essere un repository Git con working tree tracciato pulito. Regole complete nel [contratto delle proposte](docs/it/PROPOSAL_CONTRACT.md).

Le proposte pendenti si possono modificare dalla pagina di dettaglio della UI web. Le proposte applicate, merged, rejected, withdrawn o archived sono in sola lettura.

## API JSON per agenti

Gli agenti esterni possono creare, elencare, leggere, modificare, generare, rifiutare e ritirare proposte pendenti tramite l'API JSON locale. Non esiste intenzionalmente un endpoint di approvazione: serve la revisione umana.

```bash
curl -X POST http://localhost:8080/api/proposals \
  -H 'Content-Type: application/json' \
  --data @proposta.json
```

Vedi la [guida API JSON](docs/it/API.md) per endpoint, codici di stato ed esempi.

## LLM locale opzionale

L'adapter può solo creare proposte pendenti. Non può approvare né scrivere dati canonici. Usa la pagina **Generate** nella UI web o la CLI.

```bash
ollama serve
ollama pull llama3.2
storygram proposal generate --text "Nonna diceva che viveva vicino alla stazione." --model llama3.2
storygram proposal generate --file intervista.txt --json
```

Configurazione: `--provider`, `--url`, `--model`, `$STORYGRAM_LLM_PROVIDER`, `$STORYGRAM_LLM_URL`, `$STORYGRAM_LLM_MODEL` e `$STORYGRAM_LLM_API_KEY`. Ollama rispetta anche `$STORYGRAM_OLLAMA_URL` e `$STORYGRAM_OLLAMA_MODEL`. Per un server compatibile OpenAI usa `--provider openai --url http://host:8080 --model qwen3-4b`; tieni la chiave nell'ambiente, non nel repository. Gli errori del provider non toccano i dati canonici e vengono mostrati nella UI.

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

## Container

Il repository include `Dockerfile`, `compose.yaml` e un entrypoint con auto-inizializzazione. L'immagine è stata costruita e verificata end-to-end tramite un daemon host compatibile Docker (Podman Engine 5.8.2 via Docker CLI): avvio non-root, auto-init, healthcheck, applicazione di una proposta nel container, persistenza dopo restart/ricreazione e bind mount host sono tutti passati.

```bash
STORYGRAM_PORT=18080 docker compose -p storygram-test up --build -d
docker compose -p storygram-test ps
# Profilo Ollama opzionale:
docker compose -p storygram-test --profile llm up -d
docker compose -p storygram-test exec ollama ollama pull llama3.2
```

L'immagine predefinita funziona senza Ollama. I dati persistono nel volume `storygram-data`, la UI ascolta sulla porta 8080 e il container gira come utente non-root `storygram` (UID/GID 100:101). Per un bind mount, crea la directory host e assegnale quell'UID/GID; scoprili con `docker run --rm --entrypoint id storygram:local`. Imposta `STORYGRAM_AUTO_INIT=0` per disabilitare l'inizializzazione automatica di archivio e Git. Usa un nome progetto e una porta unici per i test e rimuovi solo le risorse create.

## Struttura

- `data/` record canonici revisionati
- `inbox/` import non revisionati
- `proposals/` proposte pendenti locali
- `media-manifest/` manifest con checksum dei media
- `generated/` viste derivate ricostruibili
- `schema/` schemi JSON canonici

## Sviluppo

```bash
PYTHONPATH=/data/src python -m pytest -q
ruff check src tests
ruff format --check src tests
mypy src

PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm install
npm run test:e2e
```

I test browser usano Node Playwright con Chromium di sistema. Su Alpine: `apk add chromium nodejs npm`.

## Documentazione

- [Guida italiana](docs/it/README.md)
- [API JSON](docs/it/API.md)
- [English guide](docs/en/README.md)
- [README (English)](README.md)

## Filosofia

- L'episodio è una cattura, non un fatto; le asserzioni portano evidenza.
- `valid_time` resta separato da `transaction_time`.
- I conflitti restano espliciti e non vengono mai risolti automaticamente.
- Le correzioni usano la supersession; la storia non viene sovrascritta.
- I record si archiviano o supersedono; non si cancellano silenziosamente.
- Il nucleo deterministico resta senza LLM; l'AI può solo proporre modifiche da revisionare.
