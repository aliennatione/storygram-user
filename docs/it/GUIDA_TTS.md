# Guida vocale all'installazione e all'uso di Storygram

Questa guida è scritta per essere letta da un sintetizzatore vocale.
Le frasi sono brevi.
I comandi sono riportati anche in blocchi di codice.

## Cos'è Storygram

Storygram è un archivio locale per storie di vita.
Conserva episodi, fonti, persone, luoghi, eventi, relazioni, asserzioni, conflitti e narrazioni.
Il nucleo è deterministico.
Funziona anche senza intelligenza artificiale.
Tutti i dati canonici restano in una cartella chiamata data.

## Regola principale

Un episodio è una cattura, non un fatto.
Le asserzioni portano evidenza.
Il tempo in cui qualcosa è accaduto si chiama valid time.
Il tempo in cui qualcosa è stato registrato si chiama transaction time.
I conflitti restano espliciti e non vengono risolti automaticamente.
Le correzioni creano nuovi record e non sovrascrivono la storia.
Solo un essere umano può approvare una proposta.

## Prerequisiti

Serve Python versione tre punto quattordici o superiore.
Serve Git.
Serve Node e npm solo per i test del browser.
Su Alpine servono anche Chromium e Firefox per i test.

## Installazione

Apri un terminale nella cartella del progetto.
Crea un ambiente virtuale.
Digita il comando seguente.

python -m venv punto venv

Attiva l'ambiente virtuale.
Digita il comando seguente.

punto punto venv barra bin barra activate

Installa il progetto.
Digita il comando seguente.

pip install meno e punto quadra dev quadra

## Creare un archivio

Scegli una cartella per l'archivio.
Digita il comando seguente.

storygram init punto barra archivio

Inizializza Git nella cartella.
Digita i comandi seguenti.

cd archivio
git init

Valida l'archivio.
Digita il comando seguente.

storygram validate

## Avviare l'interfaccia web

Digita il comando seguente.

storygram web meno meno archive punto barra archivio meno meno host zero punto zero punto zero punto zero meno meno port ottomilaottanta

Apri il browser su http due punti barra barra localhost due punti ottomilaottanta.
Puoi cambiare lingua con il selettore en it nell'header.

## Creare una proposta con la riga di comando

Prepara un file json con la proposta.
Digita il comando seguente.

storygram proposal new meno meno file proposta punto json

Elenca le proposte pendenti.
Digita il comando seguente.

storygram proposal list

Mostra una proposta.
Digita il comando seguente.

storygram proposal show proposta due punti esempio meno uno

## Revisionare e approvare

Controlla il dry run prima di approvare.
Digita il comando seguente.

storygram proposal approve proposta due punti esempio meno uno meno meno dry run

Se il dry run è valido, approva.
Digita il comando seguente.

storygram proposal approve proposta due punti esempio meno uno

L'approvazione scrive i dati canonici e crea un commit Git.

## Rifiutare o ritirare

Rifiuta una proposta con una motivazione.
Digita il comando seguente.

storygram proposal reject proposta due punti esempio meno uno meno meno reason virgolette manca evidenza virgolette

Ritira una proposta già in attesa.
Digita il comando seguente.

storygram proposal withdraw proposta due punti esempio meno uno meno meno reason virgolette sorgente errata virgolette

## Usare l'interfaccia web

Apri la pagina aggiungi memoria per creare una proposta episodio.
Apri la pagina aggiungi fonte per registrare evidenza.
Apri la pagina aggiungi entità per creare luoghi, eventi, organizzazioni e periodi.
Apri la pagina aggiungi persona per creare una persona.
Apri la pagina aggiungi relazione per creare una relazione familiare.
Apri la pagina aggiungi asserzione per creare un fatto con soggetto, predicato e oggetto.
Tutte queste pagine creano solo proposte pendenti.
L'approvazione resta obbligatoria.

## Consultare i record

Apri la pagina records per filtrare per tipo, stato, visibilità o testo.
Apri il dettaglio di un record per vedere il json grezzo e i collegamenti.
La pagina timeline mostra le asserzioni aperte ordinate per tempo.
La pagina genogram è sperimentale e mostra le relazioni di una persona.
La pagina conflicts mostra i conflitti espliciti e quelli derivati.

## Export e import

Esporta i record in json.
Digita il comando seguente.

storygram export meno meno format json

Esporta in yaml o markdown.
Digita il comando seguente.

storygram export meno meno format yaml

Importa un export come proposta pendente.
Digita il comando seguente.

storygram import file punto json

L'import non scrive mai in data.
Serve sempre l'approvazione umana.

## Container opzionale

Costruisci l'immagine.
Digita il comando seguente.

docker build meno t storygram due punti local punto

Avvia con compose.
Digita il comando seguente.

storygram port uguale a ottomilaottanta docker compose meno p storygram test up meno meno build meno d

I dati persistono nel volume nominato storygram data.

## LLM opzionale

L'adapter crea solo proposte pendenti.
Non approva e non scrive dati canonici.
Configura il provider con variabili d'ambiente.
Usa qwen tre trattino b come modello di riferimento.
Esegui sempre il dry run prima dell'approvazione.

## Fine

Questa guida descrive l'installazione e l'uso base.
Per i dettagli consulta i documenti nella cartella docs.