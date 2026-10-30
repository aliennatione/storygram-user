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

La UI web usa lo stesso motore, inclusa una pagina **Generate** per Ollama locale:

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

## Generazione LLM opzionale

```bash
ollama serve
ollama pull llama3.2
storygram proposal generate --text "Un ricordo..." --model llama3.2 --archive ./archive
```

L'adapter forza `status=proposed`, scarta i campi sconosciuti e salva solo in `proposals/`. Non può approvare, applicare o modificare record canonici. Usa `--no-save` per controllare senza scrivere. La pagina **Generate** della UI usa lo stesso adapter; gli errori del provider vengono mostrati senza scrivere nulla.

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

Sono inclusi `Dockerfile` e `compose.yaml`. Non sono stati eseguiti in questa sessione di sviluppo. Su un host con Docker:

```bash
docker compose up --build -d
docker compose --profile llm up -d
docker compose exec ollama ollama pull llama3.2
```

Il container predefinito inizializza automaticamente `/data` e Git quando serve, gira come UID/GID 1000 e persiste i dati in un volume nominato. Imposta `STORYGRAM_AUTO_INIT=0` per disattivare. Il profilo Ollama è opzionale; il nucleo deterministico e la UI funzionano senza.
