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
```

`approve` scrive in modo atomico e crea un commit Git limitato ai file applicati. Usa `--no-commit` per saltare Git. L'archivio deve essere un repository Git con working tree tracciato pulito. Regole complete nel [contratto delle proposte](docs/it/PROPOSAL_CONTRACT.md).

Le proposte pendenti si possono modificare dalla pagina di dettaglio della UI web. Le proposte applicate, merged, rejected o archived sono in sola lettura.

## API JSON per agenti

Gli agenti esterni possono creare, elencare, leggere e modificare proposte pendenti tramite l'API JSON locale. Non esiste intenzionalmente un endpoint di approvazione: serve la revisione umana.

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

Configurazione: `--ollama-url`, `--model`, `$STORYGRAM_OLLAMA_URL`, `$STORYGRAM_OLLAMA_MODEL`. Gli errori del provider non toccano i dati canonici e vengono mostrati nella UI.

## Container

Il repository include `Dockerfile`, `compose.yaml` e un entrypoint con auto-inizializzazione. Questi file vanno costruiti e verificati su un host con Docker; non sono stati eseguiti nel container Alpine di sviluppo di questa sessione.

```bash
docker compose up --build -d
# Profilo Ollama opzionale:
docker compose --profile llm up -d
docker compose exec ollama ollama pull llama3.2
```

L'immagine predefinita funziona senza Ollama. I dati persistono nel volume `storygram-data`, la UI ascolta sulla porta 8080 e il container gira come utente non-root. Per un bind mount, assicurati che la directory host sia scrivibile da UID/GID 1000. Imposta `STORYGRAM_AUTO_INIT=0` per disabilitare l'inizializzazione automatica di archivio e Git.

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
