# 📚 Agenda Virtual Escolar

Agenda escolar web en català amb **Python + Flask + SQLite**.

## Inclou
- Inici amb apartat **Proper**.
- Calendari mensual.
- Deures, exàmens i esdeveniments amb descripció, data, hora i lloc.
- Assignatures i horari.
- Fitxers i imatges adjunts.
- Els adjunts dels **deures** s'eliminen quan el deure es marca com acabat.
- Paperera amb restauració i conservació configurable.
- Contrasenya amb hash.
- Exportació JSON i còpia SQLite.
- Menú superior configurable.
- Disseny responsive.

## Instal·lació

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Després obre `http://localhost:5000`.

La primera vegada et demanarà crear la contrasenya.

## Dades

La base de dades es crea a `instance/agenda.sqlite3`. Els fitxers pujats es guarden a `uploads/` i les còpies a `backups/`. Aquestes dades estan excloses de Git.

> Per publicar-la cal un servidor Python/Flask. GitHub Pages per si sol no pot executar aquest backend.
