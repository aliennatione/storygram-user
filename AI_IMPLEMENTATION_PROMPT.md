# Prompt operativo — Implementazione di Storygram

Sei l'agente AI incaricato di implementare Storygram in questo repository.

## Missione

Realizza un archivio locale, canonico, versionabile e interoperabile per episodi, fonti, persone, luoghi, eventi, relazioni, asserzioni, conflitti, narrazioni e viste derivate. Il nucleo deve funzionare senza LLM. L'AI futura sarà un adapter che produce proposte evidenziate e approvabili.

Il modello centrale è:

```text
Episode → Annotation → Assertion → Entity/Event/Relationship → Timeline/Genogram/Narrative
```

## Lettura obbligatoria

Prima di modificare file:

1. leggi `AGENTS.md`;
2. leggi `PRD.md`;
3. leggi `README.md`, se presente;
4. ispeziona codice, test, configurazioni, CI e stato Git;
5. esegui i controlli già disponibili e registra i fallimenti preesistenti.

`AGENTS.md` contiene regole generali. `PRD.md` contiene i requisiti specifici di Storygram ed è il riferimento di prodotto.

## Vincoli fondamentali

- Non partire dall'agente AI, dal chatbot o dagli embedding.
- Non trattare un episodio come un fatto.
- Non trasformare automaticamente un'asserzione in `confirmed`.
- Non sovrascrivere un'asserzione storica materialmente diversa.
- Non cancellare fonti, asserzioni o conflitti: archivia, invalida o supersedi.
- Non fare merge automatico di persone.
- Non usare dati personali reali nelle fixture.
- Non modificare il canonico senza una modifica reviewable e validata.
- Non dichiarare completato un requisito senza test o verifica riproducibile.

## Piano di lavoro

### Fase 1 — Ricognizione

- Elenca il repository e individua la struttura esistente.
- Verifica stack, package manager, test, linter, type checker e CI.
- Esegui la suite iniziale.
- Confronta lo stato con `PRD.md`.
- Proponi il primo incremento minimo completo.

### Fase 2 — Bootstrap

Se necessario:

- configura packaging e ambiente riproducibili;
- crea una CLI con `--help` e versione;
- configura test, formatter, linter e type checker;
- aggiorna README con installazione e primo comando;
- garantisci che le operazioni core funzionino offline.

### Fase 3 — Schema e modello

Implementa i tipi indicati dal PRD, iniziando da:

```text
Episode
Assertion
Source
Annotation
Person
Place
Event
Relationship
```

Per ogni tipo crea:

- schema machine-readable;
- modello applicativo;
- fixture valida;
- fixture invalida;
- documentazione di campi e invarianti;
- test di parsing e validazione.

### Fase 4 — Episode

Implementa un Episode append-only o immutabile con:

- ID stabile;
- `episode_type`;
- titolo e descrizione;
- timestamp di cattura/importazione;
- autore, registratore o importer;
- partecipanti;
- riferimento alla fonte e ai media;
- checksum quando disponibile;
- visibilità;
- stato;
- collegamenti a trascrizioni o documenti.

L'ingestione di un episodio deve solo registrare l'episodio e, se previsto, creare proposte o asserzioni `reported`/`proposed`. Non deve creare fatti confermati in modo implicito.

### Fase 5 — Assertion

Implementa asserzioni con:

```text
subject
predicate
object opzionale
valid_time
transaction_time
status
certainty
confidence
asserted_by
produced_by
supported_by
annotations
supersedes
revises
contradicts
corroborates
```

Se il PRD o lo schema richiedono nomi leggermente diversi, mantieni un vocabolario coerente e documenta la scelta.

### Fase 6 — Bitemporalità

Implementa due assi distinti:

```yaml
valid_time:
  start: "1987"
  end: "1995"
  precision: year
transaction_time:
  recorded_at: "2026-10-07T10:00:00+02:00"
  recorded_until: null
```

Quando arriva una correzione storica:

1. non modificare materialmente l'asserzione precedente;
2. chiudi `recorded_until` oppure marcala `superseded`;
3. crea una nuova asserzione con ID diverso;
4. collega le due asserzioni con `supersedes`, `revises` o `contradicts`;
5. conserva le fonti originali;
6. registra autore, data e motivazione della modifica;
7. mantieni separata la validità storica dal momento della registrazione.

Aggiungi test che permettano di rispondere separatamente a:

- quale versione era registrata in una certa data;
- quale validità storica è rappresentata;
- quale asserzione è attualmente accettata;
- quali versioni sono contestate o supersedute.

### Fase 7 — Conflitti

Implementa almeno una forma di conflitto esplicito:

```yaml
assertion_a: assertion:01
assertion_b: assertion:02
relation: contradicts
status: open
reason: "Le fonti indicano anni diversi."
```

Se introduci un tipo `Conflict`, collegalo a entrambe le asserzioni e conserva:

- categoria del conflitto;
- stato (`open`, `under_review`, `resolved`, `accepted_as_plural`);
- evidenze considerate;
- revisore;
- motivazione;
- decisione;
- timestamp.

Le query e le viste devono mostrare entrambi i lati del conflitto. Una narrazione deve esplicitare il disaccordo, motivare la scelta di una versione oppure omettere la pretesa contestata.

### Fase 8 — Git canonico

Implementa una separazione chiara:

```text
data/       canonico revisionato
inbox/       import non revisionati
proposals/   modifiche proposte
media-manifest/ manifest con checksum dei media esterni
generated/   viste ricostruibili
```

Implementa o prepara comandi equivalenti a:

```bash
storygram validate
storygram rebuild
storygram git-check [BASE]
```

`git-check` deve poter:

- individuare file canonici cambiati;
- validare solo i file interessati o l'archivio completo;
- produrre output umano e JSON;
- indicare riferimenti rotti e cambiamenti incompatibili;
- essere utilizzabile in pre-commit o CI.

Non assumere che Git sia sufficiente per la query bitemporale: il commit conserva la storia del repository, mentre i campi di transaction time consentono query di dominio. Usa entrambi.

Per media grandi o privati, conserva nel Git un manifest con:

```yaml
uri: ...
sha256: ...
mime_type: ...
size: ...
visibility: private|restricted|family|public
captured_at: ...
```

### Fase 9 — Query e viste

Dopo il nucleo dati implementa:

```bash
storygram search QUERY
storygram timeline ID
storygram genogram ID
storygram conflicts --status open
storygram export --format json
storygram export --format jsonld
```

Le viste devono derivare dal canonico e linkare ID, fonti, annotazioni, status e conflitti.

### Fase 10 — Test, documentazione e CI

Aggiungi test per:

- episode valido e invalido;
- assertion valida e invalida;
- riferimenti mancanti;
- date parziali e intervalli aperti;
- correzione bitemporale;
- supersessione e contraddizione;
- conflitto irrisolto e risolto;
- filtraggio per visibilità;
- round-trip JSON/YAML;
- `git-check` su file validi e invalidi;
- dataset vuoto e dataset sintetico grande.

Aggiorna documentazione con esempi eseguibili. Esegui formatter, lint, type check, unit test, integration test e build/package check.

## Criteri di completamento MVP

Il primo MVP è completo solo quando:

- `init` crea un archivio valido;
- Episode e Assertion sono validati da schema;
- l'ingestione non conferma automaticamente i fatti;
- un conflitto mantiene entrambe le versioni e le fonti;
- una correzione storica crea una nuova versione senza cancellare la precedente;
- transaction time e valid time sono interrogabili separatamente;
- Git/CI rileva dati canonici invalidi;
- timeline e genogramma sono ricostruibili;
- JSON e JSON-LD funzionano secondo la documentazione;
- privacy e visibilità sono testate;
- tutto il core funziona senza LLM;
- documentazione e report consentono riproduzione da parte di un nuovo sviluppatore.

## Formato del report

Concludi ogni unità con:

```text
## Summary
- ...

## Files changed
- ...

## Checks run
- `command`: result

## Model/API changes
- ...

## Assumptions
- ...

## Known limitations
- ...

## Next recommended task
- ...
```

Inizia ora dalla ricognizione del repository e dalla verifica dello stato iniziale. Poi implementa il primo incremento minimo completo, senza introdurre ancora l'agente AI.
