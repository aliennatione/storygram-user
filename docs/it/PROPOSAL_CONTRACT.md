# Contratto delle proposte v1

Questo contratto è condiviso da CLI, UI web locale, agenti esterni e adapter LLM.

## File e directory

- Proposte pendenti: `proposals/<nome>.json`, ignorate da Git.
- Proposte applicate: `data/proposals/<nome>.json`, committate.
- Record canonici: `data/<directory-tipo>/<record>.json`.
- Gli ID delle proposte usano `proposal:<slug>`.
- Gli ID delle proposte applicate non vanno mai riutilizzati. Gli archivi esistenti non vengono sovrascritti.

## Forma della proposta

Campi obbligatori: `id`, `type` (`Proposal`), `status`, `created_at`, `updated_at`, `operations`.

Campi opzionali utili: `title`, `target_ids`, `evidence`, `rationale`, `confidence`, `approval_state`, `notes`.

Stati ammessi: `draft`, `proposed`, `under_review`, `approved`, `rejected`, `merged`, `archived`.

L'approvazione è consentita solo da `draft`, `proposed`, `under_review` o `approved`. Una proposta rifiutata, merged o archiviata non può essere approvata.

```json
{
  "id": "proposal:example-1",
  "type": "Proposal",
  "status": "proposed",
  "created_at": "2026-10-30T12:00:00+00:00",
  "updated_at": "2026-10-30T12:00:00+00:00",
  "title": "Aggiungi un ricordo d'infanzia",
  "evidence": ["episode:interview-1"],
  "operations": [
    {
      "op": "create",
      "record_type": "Assertion",
      "record": {
        "id": "assertion:home-1990",
        "type": "Assertion",
        "subject": "person:nonna",
        "predicate": "relation:lived_in",
        "object": "place:home",
        "status": "reported",
        "valid_time": {"start": "1990", "end": "1995", "precision": "year"},
        "transaction_time": {"recorded_at": "2026-10-30T12:00:00+00:00"},
        "created_at": "2026-10-30T12:00:00+00:00",
        "updated_at": "2026-10-30T12:00:00+00:00"
      }
    }
  ]
}
```

## Operazioni

Ogni operazione richiede `op` e `record_type`. I tipi proponibili sono 14; Proposal stesso non è proponibile.

### create

- Richiede `record`.
- L'`id` del record deve corrispondere a `record_type` e non deve esistere già.
- Il record completo deve superare il proprio schema.
- L'evidenza viene ereditata da quella della proposta e dell'operazione.

### update_metadata

- Richiede `target_id` e `fields` non vuoto.
- Il target deve esistere e corrispondere a `record_type`.
- Si possono modificare solo i campi nell'allowlist del tipo.
- `id`, `type` e `created_at` non sono modificabili.
- `updated_at` viene impostato da Storygram.
- Non serve evidenza: sono metadati amministrativi, non asserzioni fattuali.

### supersede

- Richiede `target_id` e `record`.
- Solo Episode e Assertion supportano la supersession.
- Il sostituto deve essere un nuovo record dello stesso tipo e contenere `target_id` in `supersedes`.
- Per le Assertion, Storygram marca il vecchio record come `superseded` e chiude `transaction_time.recorded_until` con il `transaction_time.recorded_at` del sostituto.
- Il record originale non viene mai cancellato o sovrascritto con il sostituto.

### archive

- Richiede `target_id`.
- Ogni tipo tranne Conflict e Proposal può essere archiviato.
- L'archiviazione imposta `status` a `archived`; non cancella i record.
- L'evidenza è obbligatoria solo quando il tipo dichiara `evidence_required`.

## Evidenza

- L'evidenza a livello di proposta vale per tutte le operazioni semantiche; quella a livello di operazione si aggiunge.
- L'evidenza deve esistere nei dati canonici o essere creata prima nella stessa proposta.
- Sono accettati solo riferimenti `episode:`, `source:` e `annotation:`.
- Le Assertion create o superseded senza evidenza vengono rifiutate.
- Episode è una cattura, quindi le operazioni su Episode non richiedono evidenza separata.

## Protezione dai conflitti

- Le Assertion nuove o superseded vengono confrontate con tutte le Assertion aperte.
- Stesso `subject` e `predicate` con `object`/`value` diverso e validità sovrapposta è un potenziale conflitto.
- Un record Conflict esplicito che contiene entrambi gli ID delle asserzioni sblocca l'operazione.
- Senza quel Conflict, l'approvazione fallisce con un errore che nomina entrambe le asserzioni.
- I Conflict usano `open`, `under_review`, `resolved`, `accepted_as_plural`, `rejected`.

## Risultato dell'apply

Un'approvazione riuscita restituisce:

```json
{
  "ok": true,
  "proposal_id": "proposal:example-1",
  "dry_run": false,
  "commit": "<git-hash-o-null>",
  "operations": [{"op": "create", "record_type": "Assertion", "record_id": "assertion:home-1990", "evidence": ["episode:interview-1"]}],
  "files": ["data/assertions/assertion_home-1990.json", "data/proposals/proposal_example-1.json"]
}
```

Tutti gli errori di validazione vengono raccolti prima di scrivere. Se la pianificazione fallisce, non viene scritto nulla.

## Confine dell'adapter

- Gli adapter ricevono testo sorgente e, opzionalmente, ID canonici noti, e restituiscono una sola proposta.
- Gli adapter possono creare solo proposte `proposed`; non possono approvare, applicare o archiviare.
- Storygram normalizza l'output: `type` è `Proposal`, `status` è `proposed`, i timestamp sono nuovi e i campi top-level sconosciuti vengono scartati.
- `save_pending` valida lo schema della proposta e scrive solo in `proposals/`.
- La pagina Generate della UI e la CLI usano lo stesso adapter e lo stesso percorso di salvataggio; gli errori del provider non toccano mai i dati canonici.
- Il motore di apply resta l'unico percorso verso i dati canonici e richiede sempre un'approvazione umana esplicita.
- I provider sono sostituibili. Il provider Ollama predefinito chiama `/api/generate` con `stream: false` e `format: "json"`.
