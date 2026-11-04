---
name: demo-authoring
description: Use when the user asks to create demos, examples, guides, tutorials, animations, or recorded courses about Storygram or any topic. Covers installing and using Manim (Python animations) and VCR (Virtual Course Recorder, Canonical, Slidev-based courses) plus a Slidev fallback. Output is derived and gitignored; never touches canonical data.
---

# Demo Authoring — Manim e VCR

Skill opzionale per creare materiale dimostrativo (demo, esempi, guide, tutorial, animazioni, corsi registrati) per Storygram o per qualsiasi altro argomento. Non tocca mai `data/` né il core dell'applicazione: tutto l'output è derivato e finisce in `generated/demos/` (gitignored).

## Guardrail

- Il core di Storygram resta deterministico e senza LLM: questa skill è solo uno strumento di authoring.
- Non scrivere mai in `data/`, `proposals/` o `inbox/`. Output solo in `generated/demos/`.
- Usare solo dati sintetici negli esempi.
- Verificare gli strumenti prima di usarli (`scripts/demo_tools.py status`).
- Le sessioni e i container di sviluppo sono volatili: reinstallare/reverificare prima di ogni uso.

## Strumenti

### Manim (Manim Community)

- Libreria Python per animazioni matematiche/visive.
- Installazione (Alpine/dev container): `apk add ffmpeg cairo pango pango-dev texlive fontconfig ttf-dejavu build-base python3-dev` poi `pip install --break-system-packages manim`.
- Comando base: `manim -ql scene.py ClassName` (low quality, veloce) oppure `-qm`/`-qh`.
- Verifica: `manim --version`.

### VCR (Virtual Course Recorder, Canonical)

- Strumento snap (Ubuntu) basato su Slidev + VHS + Playwright + FFmpeg + Piper TTS.
- Installazione (Ubuntu host con snapd): `sudo snap install video-course-recorder --edge`, poi `sudo snap alias video-course-recorder vcr`.
- Richiede un content repo con `modules/<modulo>/<locale>/index.md` e `package.json`.
- Comandi chiave: `vcr dev`, `vcr render-audio`, `vcr render-terminal`, `vcr render-playwright`, `vcr record-video`, `vcr build-slides`, `vcr export-slides`.
- **Non installabile su Alpine**: snapd non è disponibile. In questo container usare il fallback Slidev.

### Fallback Slidev (disponibile in questo container)

- Installazione: `npm install -g @slidev/cli @slidev/theme-default`.
- Build: `slidev build slides.md --out dist`.
- Dev: `slidev slides.md`.

## Probe di capacità

Eseguire sempre prima di lavorare:

```bash
PYTHONPATH=/data/src python /data/scripts/demo_tools.py status
```

Il comando stampa JSON con disponibilità e versioni di `manim`, `vcr`, `slidev`, `ffmpeg`, `texlive`.

## Workflow 1 — Animazione Manim

1. Creare la scena: `PYTHONPATH=/data/src python /data/scripts/demo_tools.py scaffold manim <nome>`.
   - Genera `generated/demos/manim/<nome>.py` dal template.
2. Modificare la scena (classe `DemoScene`).
3. Renderizzare: `PYTHONPATH=/data/src python /data/scripts/demo_tools.py render manim generated/demos/manim/<nome>.py`.
   - Output in `generated/demos/manim/media/`.
4. Verificare il file MP4 prodotto.

Template: `.opencode/skills/demo-authoring/templates/manim_scene.py`.

## Workflow 2 — Corso VCR (Ubuntu host)

1. Creare content repo: `PYTHONPATH=/data/src python /data/scripts/demo_tools.py scaffold vcr <modulo>`.
   - Genera `generated/demos/vcr/<modulo>/en/index.md` + `package.json`.
2. Su host Ubuntu con VCR installato: `cd generated/demos/vcr/<modulo> && pnpm install && vcr dev <modulo>`.
3. Aggiungere blocchi `terminal`, `playwright`, `speech` come da docs VCR.
4. Renderizzare asset: `vcr render-terminal <modulo>`, `vcr render-playwright <modulo>`, `vcr render-audio <modulo>`.
5. Registrare: `vcr record-video <modulo>`.

## Workflow 3 — Corso Slidev (fallback in questo container)

1. Scaffold VCR come sopra (il markdown è Slidev-compatibile).
2. Build: `cd generated/demos/vcr/<modulo> && slidev build en/index.md --out dist`.
3. Per dev server: `slidev en/index.md`.

## Workflow 4 — Demo Storygram (esempio)

Esempio di animazione che visualizza una timeline di eventi (dati sintetici):

```python
from manim import *

class StorygramTimeline(Scene):
    def construct(self):
        events = ["1990", "2000", "2010", "2020"]
        dots = VGroup(*[Dot() for _ in events]).arrange(RIGHT, buff=1.5)
        labels = VGroup(*[Text(e).scale(0.5).next_to(d, DOWN) for e, d in zip(events, dots)])
        self.play(Create(dots), Write(labels))
        self.wait(1)
```

## Installazione (comandi riassuntivi)

### Manim (Alpine)

```bash
apk add --no-cache ffmpeg cairo pango pango-dev texlive fontconfig ttf-dejavu build-base python3-dev
pip install --break-system-packages manim
manim --version
```

Helper: `PYTHONPATH=/data/src python /data/scripts/demo_tools.py install manim --yes`.

### VCR (Ubuntu)

```bash
sudo snap install video-course-recorder --edge
sudo snap alias video-course-recorder vcr
vcr --help
```

### Slidev (fallback)

```bash
npm install -g @slidev/cli @slidev/theme-default
slidev --version
```

## Output e percorsi

- Manim: `generated/demos/manim/` (scene `.py`, `media/` con MP4).
- VCR/Slidev: `generated/demos/vcr/<modulo>/`.
- Tutto gitignored tramite `generated/`.

## Verifica rapida

```bash
PYTHONPATH=/data/src python /data/scripts/demo_tools.py status
# manim presente -> render di prova
PYTHONPATH=/data/src python /data/scripts/demo_tools.py scaffold manim demo_prova
PYTHONPATH=/data/src python /data/scripts/demo_tools.py render manim generated/demos/manim/demo_prova.py
```

## Note su volatilità

- Container e sessioni sono volatili: prima di usare, rieseguire `status` e reinstallare se necessario.
- Le dipendenze di sistema (texlive, ffmpeg) sono pesanti (~1.5 GB); documentare in `docs/dev/STATE.md` se installate.
- Non committare mai `generated/` né dipendenze di sistema.
EOF
echo done