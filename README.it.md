# Storygram

Archivio locale, versionabile e interoperabile per episodi, fonti, persone, luoghi, eventi, relazioni, asserzioni, conflitti e narrazioni. Il nucleo funziona offline senza LLM.

## Struttura
- `data/` - record canonici revisionati
- `inbox/` - import non revisionati
- `proposals/` - modifiche proposte in attesa di revisione
- `media-manifest/` - manifest con checksum dei media
- `generated/` - viste derivate ricostruibili
- `schema/` - schemi JSON

## Avvio rapido
```bash
pip install -e ".[dev]"
storygram init ./archive
storygram validate ./archive
PYTHONPATH=/data/src python -m pytest -v
```

## Documentazione
- [Documentazione inglese](docs/en/)
- [Documentazione italiana](docs/it/)
- [README (English)](README.md)

## Filosofia
- Separazione tra episodio e fatto
- Bitemporalità (`valid_time` / `transaction_time`)
- Conflitti espliciti, mai risolti automaticamente
- Storia delle correzioni preservata (supersession)
- Nucleo deterministico senza AI
