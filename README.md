# 📚 Agenda Virtual Escolar

Agenda escolar web en català amb **Python + Flask + SQLite**.

## Funcions

- 🐍 Python + Flask
- 🗄️ SQLite amb persistència real
- 🔐 Inici de sessió amb contrasenya guardada amb hash
- 📝 Deures, exàmens i esdeveniments
- 📅 Calendari mensual
- 📚 Assignatures
- 🕒 Horari
- 📎 Fitxers i imatges adjunts
- 🗑️ Paperera amb restauració i eliminació definitiva
- 💾 Còpia SQLite i exportació JSON
- 📥 Importació JSON
- ⚙️ Configuració del menú, paperera, "Proper" i còpies automàtiques
- 📊 Estadístiques
- 🏖️ Vacances i dies lliures manuals
- 📱 Disseny adaptable a mòbil, tauleta i ordinador

### Regla dels deures

Quan un deure es marca com **acabat**, els seus fitxers i imatges s'eliminen tant del disc com de la base de dades.

## Instal·lació

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Després obre `http://localhost:5000`.

La primera vegada et demanarà crear la contrasenya.

## Estructura

- `app.py` — aplicació principal Flask i SQLite.
- `enhancements.py` — funcions avançades.
- `run.py` — arrencada de la versió completa.
- `requirements.txt` — dependències.
- `instance/agenda.sqlite3` — base de dades local, creada automàticament.
- `uploads/` — fitxers pujats.
- `backups/` — còpies de seguretat.

Les dades locals estan excloses de Git.

> GitHub Pages no executa Python/Flask; cal executar el backend en un servidor Python.
