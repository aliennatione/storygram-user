# API JSON per agenti

Il server web locale espone una piccola API JSON per inviare, generare, rifiutare e ritirare proposte **pendenti**. Non esiste un endpoint di approvazione: solo la UI umana o la CLI possono applicare una proposta.

Avvia il server:

```bash
storygram web --archive ./archive --host 0.0.0.0 --port 8080
```

## Regole

- Invia `Content-Type: application/json`.
- Gli ID delle proposte devono iniziare con `proposal:` e vanno URL-encoded nei percorsi.
- L'API può creare, modificare, generare, rifiutare e ritirare proposte pendenti.
- La modifica conserva `created_at`, aggiorna `updated_at` e non può cambiare l'ID.
- Le proposte applicate, merged, rejected, withdrawn o archived sono in sola lettura.
- Nulla in `data/` cambia finché una persona non approva la proposta.
- Non esiste un endpoint di approvazione. L'approvazione resta solo UI/CLI.
- L'API non ha autenticazione ed è pensata per una rete locale controllata.

## Elenco proposte

```http
GET /api/proposals
GET /api/proposals?include_applied=1
```

```json
{
  "ok": true,
  "proposals": [
    {
      "id": "proposal:example-1",
      "status": "proposed",
      "title": "Aggiungi un ricordo",
      "updated_at": "2026-10-30T12:00:00+00:00",
      "operation_count": 1,
      "applied": false
    }
  ]
}
```

## Creare una proposta pendente

```http
POST /api/proposals
Content-Type: application/json
```

```json
{
  "id": "proposal:agent-1",
  "type": "Proposal",
  "status": "proposed",
  "created_at": "2026-10-30T12:00:00+00:00",
  "updated_at": "2026-10-30T12:00:00+00:00",
  "title": "Invio agente",
  "operations": [
    {
      "op": "create",
      "record_type": "Episode",
      "record": {
        "id": "episode:agent-note",
        "type": "Episode",
        "episode_type": "other",
        "status": "reported",
        "created_at": "2026-10-30T12:00:00+00:00",
        "updated_at": "2026-10-30T12:00:00+00:00"
      }
    }
  ]
}
```

Una richiesta riuscita restituisce `201`, la proposta salvata e l'header `Location`. Gli ID duplicati restituiscono `409`.

## Leggere una proposta

```http
GET /api/proposals/proposal%3Aagent-1
```

La risposta include la proposta, se è applicata, gli errori di validazione del dry-run, le operazioni di preview e i file toccati.

```json
{
  "ok": true,
  "applied": false,
  "proposal": {},
  "validation": {"ok": true, "errors": []},
  "preview": [{"op": "create", "record_type": "Episode"}],
  "files": ["data/episodes/episode_example.json"]
}
```

## Modificare una proposta pendente

```http
PUT /api/proposals/proposal%3Aagent-1
Content-Type: application/json
```

Invia la proposta completa che sostituisce quella esistente. L'`id` deve coincidere con quello nel percorso. Il motore conserva `created_at`, imposta `updated_at` al momento corrente e valida il risultato con lo schema delle proposte.

Modificare una proposta applicata o chiusa restituisce `409`. Cambiare l'ID restituisce `400`.

## Generare una proposta pendente

```http
POST /api/proposals/generate
Content-Type: application/json
```

```json
{
  "source": "Nonna diceva che viveva vicino alla stazione.",
  "provider": "openai",
  "model": "qwen3-4b",
  "url": "http://127.0.0.1:8080",
  "save": true
}
```

`provider` accetta `ollama` oppure un provider compatibile OpenAI (`openai`, `llamacpp`).
`save` vale `true` per impostazione predefinita; impostalo a `false` per ottenere la
proposta senza scriverla. Le impostazioni del provider ricadono su
`$STORYGRAM_LLM_PROVIDER`, `$STORYGRAM_LLM_MODEL`, `$STORYGRAM_LLM_URL` e
`$STORYGRAM_LLM_API_KEY` del server. Ollama rispetta anche `$STORYGRAM_OLLAMA_MODEL` e
`$STORYGRAM_OLLAMA_URL`.

Una generazione salvata restituisce `201` con la proposta e la sua `location`.
Con `save` a `false` restituisce `200`. Gli errori del provider restituiscono `502`.

## Rifiutare una proposta pendente

```http
POST /api/proposals/proposal%3Aagent-1/reject
Content-Type: application/json
```

```json
{"reason": "evidenze insufficienti"}
```

Il body è opzionale e il motivo viene salvato in `notes`. Il rifiuto non modifica mai
i dati canonici. Rifiutare una proposta già chiusa restituisce `409`.

## Ritirare una proposta pendente

```http
POST /api/proposals/proposal%3Aagent-1/withdraw
Content-Type: application/json
```

```json
{"reason": "inviata per errore"}
```

Il ritiro imposta lo stato a `withdrawn` e lascia la proposta disponibile per l'audit.
Non modifica mai i dati canonici. Ritirare una proposta già chiusa restituisce `409`.

## Errori

```json
{"ok": false, "errors": ["proposal already exists: proposal:agent-1"]}
```

- `400`: JSON non valido, proposta non valida, cambio ID o body vuoto/non valido.
- `404`: proposta o route non trovata.
- `405`: metodo non consentito.
- `409`: duplicato, proposta già applicata o chiusa (inclusi rejected/withdrawn).
- `413`: body troppo grande.
- `415`: content type errato.

Non esiste intenzionalmente un endpoint `POST /api/proposals/<id>/approve`.
