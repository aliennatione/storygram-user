---
theme: default
title: Modulo demo
---

# Modulo demo

Contenuto del modulo. Aggiungi slide separate con `---`.

## Slide 2

Testo della seconda slide.

<!--
Per usare VCR (Ubuntu host), rimuovi i commenti HTML attorno ai blocchi seguenti.
I blocchi terminal/playwright/speech sono specifici di VCR e non sono evidenziati da Slidev.
-->

<!-- Esempio blocco terminal (richiede VCR)
```terminal name=demo-terminal
Set Width 1000
Set Height 400
Type "echo hello from VCR"
Enter
Sleep 1s
```
-->

<!-- Esempio blocco playwright (richiede VCR)
```playwright name=demo-browser width=1280 height=720
export default async function ({ page }) {
  await page.goto("https://example.com", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1000);
}
```
-->

<!-- Esempio blocco speech (richiede VCR + modello Piper)
```speech name=intro
Benvenuto in questa demo.
```
-->
EOF