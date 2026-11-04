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

Apri `http://localhost:8080`, consulta i record canonici in sola lettura, poi incolla o genera una proposta e controlla il dry-run prima di approvare. L'approvazione è l'unico percorso verso `data/`.

La pagina **Records** filtra per tipo, stato, visibilità o testo e apre un dettaglio in sola lettura con JSON grezzo e link a riferimenti e backlink. Gli stessi filtri alimentano i download di export JSON, JSON-LD, YAML e Markdown da `/export`; la pagina non espone route di scrittura, quindi le modifiche canoniche richiedono ancora una proposta e l'approvazione umana.

Il modulo **Aggiungi memoria** trasforma testo libero in una proposta Episode in attesa, con titolo, data, partecipanti, tag e visibilità opzionali. Il modulo **Aggiungi fonte** registra evidenza documentale o orale; il modulo **Aggiungi entità** crea luoghi, eventi, organizzazioni e periodi supportati da evidenza; i moduli **Aggiungi persona** e **Aggiungi relazione** creano proposte in attesa supportate da evidenza per persone e relazioni familiari, con intervalli di valid-time opzionali; il modulo **Aggiungi asserzione** crea proposte Assertion supportate da evidenza con soggetto, predicato di relazione, record oggetto o valore letterale, stato e valid-time opzionale; i moduli **Aggiungi annotazione**, **Aggiungi narrazione** e **Aggiungi conflitto** creano proposte supportate da evidenza per annotazioni, narrazioni e conflitti espliciti. Collection è ora parte del modulo **Aggiungi entità**. Una pagina **Media** in sola lettura elenca le voci del manifest checksummato registrate con `storygram media add`. Non scrivono mai dati canonici; l'approvazione resta obbligatoria. L'interfaccia è disponibile in inglese e italiano tramite il selettore EN/IT nell'header.

La pagina **Conflitti** unisce i record Conflict espliciti con le contraddizioni derivate dai collegamenti delle asserzioni; è in sola lettura e filtra per stato. Le pagine di dettaglio dei record elencano le proposte correlate che li hanno creati o modificati, e le pagine delle proposte rilinkano i record interessati, così ogni modifica è tracciabile in entrambe le direzioni.

La pagina **Timeline** mostra timeline a livello archivio o per entità, luogo e collezione dalle asserzioni aperte, con link ad asserzioni, record ed evidenze. La pagina **Genogram** è una vista relazionale sperimentale in sola lettura con badge per i predicati supportati, warning e intervalli temporali sia rappresentativi sia aggregati. La pagina **Conflitti** unisce i record Conflict espliciti con le contraddizioni derivate dai collegamenti delle asserzioni, filtra per stato e collega entrambe le asserzioni e le evidenze. Nessuna delle tre espone route di scrittura.

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

`storygram proposal show proposal:example-1 --json` stampa la proposta come JSON leggibile dalla macchina per gli agenti; una proposta mancante restituisce un `{"ok": false, "errors": [...]}` strutturato con codice di uscita 1. `approve` scrive in modo atomico e crea un commit Git limitato ai file applicati. Usa `--no-commit` per saltare Git. L'archivio deve essere un repository Git con working tree tracciato pulito. Regole complete nel [contratto delle proposte](docs/it/PROPOSAL_CONTRACT.md).

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

Configurazione: `--provider`, `--url`, `--model`, `$STORYGRAM_LLM_PROVIDER`, `$STORYGRAM_LLM_URL`, `$STORYGRAM_LLM_MODEL` e `$STORYGRAM_LLM_API_KEY`. Regola la generazione con `$STORYGRAM_LLM_TIMEOUT` e `$STORYGRAM_LLM_MAX_TOKENS`; il profilo Compose `llm` accetta anche `$STORYGRAM_LLM_CTX_SIZE` (default `8192`). Ollama rispetta anche `$STORYGRAM_OLLAMA_URL` e `$STORYGRAM_OLLAMA_MODEL`. Per un server compatibile OpenAI usa `--provider openai --url http://host:8080 --model qwen3-4b`; tieni la chiave nell'ambiente, non nel repository. Gli errori del provider non toccano i dati canonici e vengono mostrati nella UI.

Gli helper GGUF inclusi scaricano un modello piccolo in `models/` e avviano il profilo Compose opzionale `llm`:

```bash
scripts/download-model.sh
STORYGRAM_MODELS_DIR=<host-path>/models scripts/llm-up.sh
```

Il modello non viene mai committato ed è montato in sola lettura nel container di inferenza. Se `STORYGRAM_MODELS_DIR` non è impostata, `llm-up.sh` ricava il path host dal container di sviluppo. Il file predefinito Qwen2.5-1.5B serve solo a verificare il cablaggio, non è un riferimento di qualità: può restituire solo l'Episode catturato. Su un container con 1 CPU il file 3B non è consigliato (si carica ma non ha prodotto token in 25 minuti). Per la qualità usa un solo modello compatibile OpenAI `qwen3-4b` come riferimento ed evita di cambiare modello sul server. Esegui sempre `proposal approve --dry-run` prima dell'approvazione.

## Comandi legacy e derivati

Questi comandi sono deterministici e offline, ma alcuni restano più limitati di `PRD.md`:

- `storygram ingest episode FILE [--archive PATH] [--overwrite]` copia una cattura solo in `inbox/` e scrive un sidecar con checksum in `inbox/.storygram/<filename>.json` (`format` `storygram.capture/1`, dimensione, MIME type, SHA-256, `ingested_at`, `overwritten`). Non scrive mai in `data/` e rifiuta le sovrascritture silenziose; `--json` stampa i metadati della cattura.
- `storygram export [--format json|jsonld|yaml|markdown] [--visibility VALUE ...] [--archive PATH]` legge i record canonici dal registry, ordina per ID e fallisce su JSON malformato. Con un filtro di visibilità, i record senza `visibility` sono esclusi. `jsonld` resta una proiezione locale `@id`/`@type`, non un'espansione RDF completa. JSON, JSON-LD e YAML fanno round-trip senza perdita (JSON resta la lista nativa); Markdown usa front matter YAML più un corpo renderizzato, quindi il front matter è la fonte di verità e le modifiche solo al corpo non vengono re-importate. Non esiste un import canonico diretto: `storygram import` produce una proposta pendente, quindi revisione e approvazione passano ancora dalle proposte.
- `storygram import FILE [--format json|jsonld|yaml|markdown] [--evidence ID ...] [--id PROPOSAL_ID] [--archive PATH]` legge un export e crea una proposta pendente di soli `create`. Valida lo schema di ogni record ed esegue lo stesso planner del dry-run di approvazione prima di scrivere. I record Episode/Source/Annotation importati diventano evidenza per le operazioni successive; `--evidence` può puntare a catture già canoniche. L'import non scrive mai in `data/`: revisione e approvazione restano umane.
- `storygram media add FILE [--uri URI] [--visibility VALORE] [--acquired-at TS] [--notes TESTO] [--name ETICHETTA] [--overwrite] [--archive PATH]` registra un file media esterno in `media-manifest/` con URI, checksum SHA-256, tipo MIME, dimensioni, visibilità e metadati di acquisizione. Il file media non viene mai copiato né committato; le voci sono indirizzate per contenuto e rifiutano sovrascritture silenziose. `storygram media list [--json]` elenca le voci registrate. `--json` stampa la voce o un errore strutturato.
- `storygram rebuild [PATH]` ricostruisce solo l'indice di ricerca SQLite/FTS5. È idempotente, rimuove i record obsoleti e segnala gli input malformati.
- `storygram search QUERY [--archive PATH] [--rebuild]` cerca prima ID e tipi esatti, poi nel contenuto indicizzato. L'indice si aggiorna quando cambiano i file canonici.
- `storygram conflicts [--status VALUE] [--archive PATH]` unisce i Conflict espliciti con le contraddizioni derivate dalle asserzioni, deduplica le coppie e mostra entrambe le asserzioni con l'evidenza.
- `storygram timeline [ID] [--all] [--archive PATH]` esclude le asserzioni superseded, archived e rejected, ordina per inizio del valid-time e include i campi di evidenza. `ID` copre timeline di entità, luoghi e collezioni; una collezione include anche le asserzioni sui record che dichiarano `relation:member_of` verso di essa. `--all` costruisce una timeline a livello archivio.
- `storygram genogram ID [--archive PATH]` è sperimentale: legge le asserzioni `relation:*` e i record Relationship con estremi espliciti, segnala i predicati non supportati, avvisa sui record Relationship privi di estremi completi e deduplica le triple Assertion/Relationship equivalenti (preferendo la Relationship registrata più di recente), elencando ogni ID contribuente in `related_ids`, ed espone i dati temporali come `valid_time`/`transaction_time` del rappresentante più `valid_times`/`transaction_times` aggregati.

`validate`, `get`, `list` e `git-check` restano la superficie stabile di lettura e validazione.

## Container

Il repository include `Dockerfile`, `compose.yaml` e un entrypoint con auto-inizializzazione. L'immagine è stata costruita e verificata end-to-end tramite un daemon host compatibile Docker (Podman Engine 5.8.2 via Docker CLI): avvio non-root, auto-init, healthcheck, applicazione di una proposta nel container, persistenza dopo restart/ricreazione e bind mount host sono tutti passati.

```bash
STORYGRAM_PORT=18080 docker compose -p storygram-test up --build -d
docker compose -p storygram-test ps
# Profilo Ollama opzionale:
docker compose -p storygram-test --profile ollama up -d
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
npm run test:e2e:firefox
```

I test browser usano Node Playwright con Chromium di sistema per il flusso completo. Il flusso Firefox usa WebDriver/geckodriver con Firefox di sistema. Su Alpine: `apk add chromium firefox geckodriver nodejs npm`. `npm run test:e2e:all` esegue entrambi.

## Demo

Tutto il materiale demo è derivato e ignorato da Git in `generated/demos/`; non tocca mai i dati canonici.

Animazioni Manim (dati sintetici):

- `generated/demos/manim/media/videos/storygram_timeline/480p15/StorygramTimeline.mp4`
- `generated/demos/manim/media/videos/storygram_proposal_flow/480p15/StorygramProposalFlow.mp4`

Riproducile con qualsiasi player (ad esempio `ffplay` o `mpv`). Per ri-renderizzare:

```bash
PYTHONPATH=/data/src python scripts/demo_tools.py render manim generated/demos/manim/storygram_timeline.py
PYTHONPATH=/data/src python scripts/demo_tools.py render manim generated/demos/manim/storygram_proposal_flow.py
```

Corso Slidev di introduzione (bilingue):

- Sito generato: `generated/demos/vcr/storygram_intro/en/dist/index.html` (inglese) e `.../it/dist/index.html` (italiano). Apri uno dei due file nel browser.
- Server di sviluppo: `cd generated/demos/vcr/storygram_intro && slidev en/index.md` (oppure `it/index.md`).
- Per rigenerare: `cd generated/demos/vcr/storygram_intro && slidev build en/index.md --out dist` (e lo stesso per `it/`).

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
