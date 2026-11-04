"""English/Italian translations for the local web interface."""

from __future__ import annotations

from contextvars import ContextVar

DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ("en", "it")

_language: ContextVar[str] = ContextVar("storygram_web_language", default=DEFAULT_LANGUAGE)
_path: ContextVar[str] = ContextVar("storygram_web_path", default="/")

ITALIAN: dict[str, str] = {
    "Home": "Home",
    "Records": "Record",
    "Timeline": "Cronologia",
    "Conflicts": "Conflitti",
    "All": "Tutti",
    "open": "aperto",
    "resolved": "risolto",
    "accepted_as_plural": "accettato come pluralità",
    "derived": "derivato",
    "Relation": "Relazione",
    "Reason": "Motivo",
    "Identified": "Identificato",
    "Assertions": "Asserzioni",
    "No conflicts found.": "Nessun conflitto trovato.",
    (
        "Explicit conflict records and contradictions derived from assertion links. "
        "This view is read-only."
    ): (
        "Record di conflitto espliciti e contraddizioni derivate dai collegamenti "
        "delle asserzioni. Questa vista è in sola lettura."
    ),
    "Genogram": "Genogramma",
    "Proposals": "Proposte",
    "Add memory": "Aggiungi memoria",
    "Add source": "Aggiungi fonte",
    "Source type": "Tipo di fonte",
    "Title is required": "Il titolo è obbligatorio",
    "Unsupported source type: {value}": "Tipo di fonte non supportato: {value}",
    "New source: {title}": "Nuova fonte: {title}",
    "Created from the Add source form.": "Creata dal modulo Aggiungi fonte.",
    "Optional notes about this source": "Note opzionali su questa fonte",
    (
        "Add a source as a pending proposal. A source can support later people, "
        "relationships and assertions; it enters canonical data only after approval."
    ): (
        "Aggiungi una fonte come proposta in attesa. Una fonte può supportare "
        "persone, relazioni e asserzioni successive; entra nei dati canonici solo "
        "dopo l'approvazione."
    ),
    "oral": "orale",
    "written": "scritta",
    "archival": "archivistica",
    "registry": "anagrafica",
    "website": "sito web",
    "Add entity": "Aggiungi entità",
    "Record type": "Tipo di record",
    "Place": "Luogo",
    "Event": "Evento",
    "Organization": "Organizzazione",
    "Period": "Periodo",
    "Unsupported entity type: {value}": "Tipo di entità non supportato: {value}",
    "New {type}: {name}": "Nuovo record {type}: {name}",
    "Created from the Add entity form.": "Creato dal modulo Aggiungi entità.",
    "Optional notes about this record": "Note opzionali su questo record",
    (
        "Add a place, event, organization or period as a pending proposal. It needs "
        "existing evidence and enters canonical data only after approval."
    ): (
        "Aggiungi un luogo, un evento, un'organizzazione o un periodo come proposta "
        "in attesa. Richiede evidenza esistente ed entra nei dati canonici solo dopo "
        "l'approvazione."
    ),
    "Add person": "Aggiungi persona",
    "Name": "Nome",
    "Notes": "Note",
    "Optional notes about this person": "Note opzionali su questa persona",
    "Name is required": "Il nome è obbligatorio",
    "New person: {name}": "Nuova persona: {name}",
    "Created from the Add person form.": "Creata dal modulo Aggiungi persona.",
    "Evidence is required": "L'evidenza è obbligatoria",
    "Unknown evidence: {value}": "Evidenza sconosciuta: {value}",
    "Add a memory or source before adding this record.": (
        "Aggiungi una memoria o una fonte prima di aggiungere questo record."
    ),
    "Add assertion": "Aggiungi asserzione",
    "Add an assertion as a pending proposal. Choose a subject, a relation "
    "predicate and either an object record or a literal value. It enters "
    "canonical data only after a human approves the proposal.": (
        "Aggiungi un'asserzione come proposta in attesa. Scegli un soggetto, un "
        "predicato di relazione e un record oggetto o un valore letterale. Entra "
        "nei dati canonici solo dopo l'approvazione umana della proposta."
    ),
    "Choose a record": "Scegli un record",
    "Literal value": "Valore letterale",
    "Literal value when no object record is chosen": (
        "Valore letterale quando non si sceglie un record oggetto"
    ),
    "Value": "Valore",
    "Invalid predicate: {value}": "Predicato non valido: {value}",
    "Object or value is required": "È richiesto un oggetto o un valore",
    "Provide either an object record or a literal value, not both": (
        "Fornisci un record oggetto o un valore letterale, non entrambi"
    ),
    "Unknown record: {value}": "Record sconosciuto: {value}",
    "Unsupported status: {value}": "Stato non supportato: {value}",
    "Add at least one record before adding an assertion.": (
        "Aggiungi almeno un record prima di aggiungere un'asserzione."
    ),
    "New assertion: {subject} {predicate} {object}": (
        "Nuova asserzione: {subject} {predicate} {object}"
    ),
    "Created from the Add assertion form.": "Creata dal modulo Aggiungi asserzione.",
    "Optional notes about this assertion": "Note opzionali su questa asserzione",
    "disputed": "contestato",
    "Related proposals": "Proposte correlate",
    "Affected records": "Record interessati",
    "No proposal touches this record yet.": ("Nessuna proposta tocca ancora questo record."),
    "(pending)": "(in attesa)",
    "Add relationship": "Aggiungi relazione",
    (
        "Add a relationship as a pending proposal. It enters canonical data only "
        "after a human approves the proposal."
    ): (
        "Aggiungi una relazione come proposta in attesa. Entra nei dati canonici "
        "solo dopo l'approvazione umana della proposta."
    ),
    "Choose a person": "Scegli una persona",
    "Choose a predicate": "Scegli un predicato",
    "Start": "Inizio",
    "End": "Fine",
    "Precision": "Precisione",
    "Optional notes about this relationship": "Note opzionali su questa relazione",
    "New relationship: {subject} → {object}": "Nuova relazione: {subject} → {object}",
    "Created from the Add relationship form.": "Creata dal modulo Aggiungi relazione.",
    "Subject is required": "Il soggetto è obbligatorio",
    "Object is required": "L'oggetto è obbligatorio",
    "Unknown person: {value}": "Persona sconosciuta: {value}",
    "Subject and object must be different": "Soggetto e oggetto devono essere diversi",
    "Unsupported predicate: {value}": "Predicato non supportato: {value}",
    "Add at least two people before adding a relationship.": (
        "Aggiungi almeno due persone prima di aggiungere una relazione."
    ),
    "day": "giorno",
    "month": "mese",
    "year": "anno",
    "decade": "decennio",
    "approximate": "approssimativo",
    (
        "Add a person as a pending proposal. The person enters canonical data only "
        "after a human approves the proposal."
    ): (
        "Aggiungi una persona come proposta in attesa. La persona entra nei dati "
        "canonici solo dopo l'approvazione umana della proposta."
    ),
    "New proposal": "Nuova proposta",
    "Generate": "Genera",
    "Could not continue": "Impossibile continuare",
    "unknown": "sconosciuto",
    "draft": "bozza",
    "proposed": "proposta",
    "under_review": "in revisione",
    "approved": "approvata",
    "merged": "unita",
    "rejected": "rifiutata",
    "withdrawn": "ritirata",
    "applied": "applicata",
    "archived": "archiviata",
    "confirmed": "confermato",
    "reported": "riportato",
    "superseded": "superato",
    "Some records could not be loaded": "Alcuni record non sono stati caricati",
    "None.": "Nessuno.",
    "(missing)": "(mancante)",
    "(missing id)": "(id mancante)",
    "No proposals yet.": "Nessuna proposta.",
    "ID": "ID",
    "Status": "Stato",
    "Title": "Titolo",
    "Operations": "Operazioni",
    "Location": "Posizione",
    "Archive validates.": "L'archivio è valido.",
    "Local-first review surface. Canonical changes require approval.": (
        "Interfaccia di revisione local-first. Le modifiche canoniche richiedono approvazione."
    ),
    "Review queue": "Coda di revisione",
    "Pending": "In attesa",
    "Merged": "Unite",
    "Browse records": "Sfoglia i record",
    "Create proposal": "Crea proposta",
    "Generate with Ollama": "Genera con Ollama",
    "View proposals": "Vedi le proposte",
    "Record counts": "Conteggio record",
    (
        "Save a memory as a pending proposal. It does not enter canonical data "
        "until a human approves the proposal; use the advanced JSON editor for "
        "other record types."
    ): (
        "Salva una memoria come proposta in attesa. Non entra nei dati canonici "
        "finché una persona non approva la proposta; usa l'editor JSON avanzato "
        "per gli altri tipi di record."
    ),
    "Type": "Tipo",
    "Captured at": "Data della memoria",
    "Visibility": "Visibilità",
    "All visibilities": "Tutte le visibilità",
    "Export": "Esporta",
    "Export {format}": "Esporta {format}",
    "Unsupported export format": "Formato di esportazione non supportato",
    "Unsupported visibility": "Visibilità non supportata",
    "Could not export archive": "Impossibile esportare l'archivio",
    "Unspecified": "Non specificata",
    "Memory": "Memoria",
    "Write the memory...": "Scrivi la memoria...",
    "Participants": "Partecipanti",
    "Tags": "Tag",
    "family, torino": "famiglia, torino",
    "Save pending proposal": "Salva proposta in attesa",
    "Advanced JSON editor": "Editor JSON avanzato",
    "Cancel": "Annulla",
    "Memory text is required": "Il testo della memoria è obbligatorio",
    "Memory capture": "Acquisizione memoria",
    "Created from the Add memory form.": "Creata dal modulo Aggiungi memoria.",
    "Unsupported episode type: {value}": "Tipo di episodio non supportato: {value}",
    "Unsupported visibility: {value}": "Visibilità non supportata: {value}",
    "Unknown participant: {value}": "Partecipante sconosciuto: {value}",
    "memory": "memoria",
    "interview": "intervista",
    "letter": "lettera",
    "photograph": "fotografia",
    "audio": "audio",
    "video": "video",
    "document": "documento",
    "observation": "osservazione",
    "other": "altro",
    "private": "privata",
    "restricted": "riservata",
    "family": "famiglia",
    "public": "pubblica",
    "No records match these filters.": "Nessun record corrisponde ai filtri.",
    "Name / title": "Nome / titolo",
    "Updated": "Aggiornato",
    "File": "File",
    "Read-only canonical record browser. Showing {shown} of {total} records.": (
        "Browser dei record canonici in sola lettura. Mostrati {shown} di {total} record."
    ),
    "All types": "Tutti i tipi",
    "Search": "Cerca",
    "Filter": "Filtra",
    "Reset": "Azzera",
    "id, name, notes": "id, nome, note",
    "Not found": "Non trovato",
    "Record not found": "Record non trovato",
    "(empty id)": "(id vuoto)",
    "Back to records": "Torna ai record",
    "References": "Riferimenti",
    "Referenced by": "Referenziato da",
    "Record JSON": "JSON del record",
    "Timeline not found": "Cronologia non trovata",
    "Unknown record": "Record sconosciuto",
    "Back to archive timeline": "Torna alla cronologia dell'archivio",
    "No timeline entries for {scope}.": "Nessuna voce di cronologia per {scope}.",
    "Valid time": "Tempo valido",
    "Assertion": "Asserzione",
    "Subject": "Soggetto",
    "Predicate": "Predicato",
    "Object": "Oggetto",
    "Transaction time": "Tempo di registrazione",
    "Evidence": "Evidenza",
    "Read-only timeline derived from open assertions. Scope: {scope}.": (
        "Cronologia in sola lettura derivata dalle asserzioni aperte. Ambito: {scope}."
    ),
    "Record ID": "ID record",
    "Show timeline": "Mostra cronologia",
    "Archive timeline": "Cronologia dell'archivio",
    "Person ID": "ID persona",
    "Show genogram": "Mostra genogramma",
    "Experimental relationship view. Provide a person ID.": (
        "Vista sperimentale delle relazioni. Inserisci l'ID di una persona."
    ),
    "Provide a person ID": "Inserisci l'ID di una persona",
    "Genogram not found": "Genogramma non trovato",
    "Back to genogram": "Torna al genogramma",
    "supported": "supportato",
    "unsupported": "non supportato",
    "No relations for {person}.": "Nessuna relazione per {person}.",
    "Direction": "Direzione",
    "Supported": "Supportato",
    "Source record": "Record di origine",
    "Valid time / valid_times": "Tempo valido / valid_times",
    "Transaction time / transaction_times": "Tempo di registrazione / transaction_times",
    "Related records": "Record correlati",
    "Genogram: {person}": "Genogramma: {person}",
    "Experimental": "Sperimentale",
    (
        "This relationship view is experimental and has no temporal filter yet. "
        "It derives only from canonical records and never writes data."
    ): (
        "Questa vista delle relazioni è sperimentale e non ha ancora un filtro "
        "temporale. Deriva solo da record canonici e non scrive mai dati."
    ),
    "Read-only, derived from relation:* assertions and endpoint-aware Relationship records.": (
        "In sola lettura, derivato dalle asserzioni relation:* e dai record "
        "Relationship con endpoint."
    ),
    "Genogram warnings": "Avvisi del genogramma",
    "Paste a proposal JSON object. It is saved as pending only; approval is a separate action.": (
        "Incolla un oggetto JSON di proposta. Viene salvato solo come in attesa; "
        "l'approvazione è un'azione separata."
    ),
    "Invalid JSON: {error}": "JSON non valido: {error}",
    "Proposal must be a JSON object": "La proposta deve essere un oggetto JSON",
    "Edit proposal": "Modifica proposta",
    "Editing {id}. The proposal ID cannot change; saving replaces the pending JSON.": (
        "Modifica di {id}. L'ID della proposta non può cambiare; il salvataggio "
        "sostituisce il JSON in attesa."
    ),
    "Edit {id}": "Modifica {id}",
    "Generate proposal": "Genera proposta",
    (
        "A local model turns source text into a pending proposal. It cannot approve "
        "or write canonical data; review the dry-run first. Set "
        "STORYGRAM_LLM_API_KEY in the server environment for providers that require "
        "a key."
    ): (
        "Un modello locale trasforma il testo di partenza in una proposta in attesa. "
        "Non può approvare né scrivere dati canonici; controlla prima l'anteprima. "
        "Imposta STORYGRAM_LLM_API_KEY nell'ambiente del server per i provider che "
        "richiedono una chiave."
    ),
    "Paste an interview, note or memory...": "Incolla un'intervista, una nota o una memoria...",
    "Provider": "Provider",
    "Model": "Modello",
    "LLM URL": "URL LLM",
    "Generate pending proposal": "Genera proposta in attesa",
    "Source text is empty": "Il testo di partenza è vuoto",
    "Invalid proposal": "Proposta non valida",
    "Dry-run preview": "Anteprima dry-run",
    "Files": "File",
    "Approve and commit": "Approva ed esegui commit",
    "Approve without commit": "Approva senza commit",
    "Rejection reason (optional)": "Motivo del rifiuto (facoltativo)",
    "Reject": "Rifiuta",
    "Withdrawal reason (optional)": "Motivo del ritiro (facoltativo)",
    "Withdraw": "Ritira",
    "Edit pending proposal": "Modifica proposta in attesa",
    "Back": "Indietro",
    "Proposal JSON": "JSON della proposta",
    "Cannot edit": "Modifica non consentita",
    "Cannot edit applied proposal": "Non è possibile modificare una proposta applicata",
    "Proposal is not editable": "La proposta non è modificabile",
    "Bad request": "Richiesta non valida",
    "Method not allowed": "Metodo non consentito",
    "request body too large": "corpo della richiesta troppo grande",
    "Genogram {person}": "Genogramma {person}",
}


def normalize_language(value: str | None) -> str:
    return value if value in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def set_language(value: str | None) -> str:
    language = normalize_language(value)
    _language.set(language)
    return language


def current_language() -> str:
    return _language.get()


def set_path(value: str) -> None:
    _path.set(value or "/")


def current_path() -> str:
    return _path.get()


def t(key: str, **values: object) -> str:
    text = ITALIAN.get(key, key) if current_language() == "it" else key
    return text.format(**values) if values else text
