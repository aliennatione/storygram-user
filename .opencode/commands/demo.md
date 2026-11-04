---
description: Crea demo, esempi, guide o tutorial con Manim e/o VCR/Slidev. Argomento: topic e strumento (manim|vcr|slidev).
agent: build
---

Sei l'assistente di authoring demo per Storygram. L'argomento richiesto è: $ARGUMENTS

Segui la skill `demo-authoring`:

1. Esegui `PYTHONPATH=/data/src python /data/scripts/demo_tools.py status` per verificare gli strumenti disponibili.
2. Chiedi (se non specificato) quale strumento usare: `manim` (animazioni), `vcr` (corso Ubuntu/snap) o `slidev` (fallback presente in questo container).
3. Fai scaffold con `scaffold manim <nome>` o `scaffold vcr <modulo>`.
4. Genera contenuto nel file creato, usando dati sintetici e solo percorsi sotto `generated/demos/`.
5. Renderizza/compila e verifica l'output.
6. Non scrivere mai in `data/`, `proposals/`, `inbox/`.
7. Documenta in `docs/dev/STATE.md` se hai installato dipendenze di sistema.

Restituisci un riepilogo con percorsi dei file prodotti e comandi di verifica.