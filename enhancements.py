import os, json, sqlite3
from datetime import datetime, date, timedelta
from flask import request, redirect, url_for, flash, send_file


def register(app, mod):
    # Amplia el menú sense trencar les rutes existents.
    old_base = mod.base
    labels = {'dashboard':'Inici','calendar':'Calendari','homework':'Deures','exams':'Exàmens','events':'Esdeveniments','subjects':'Assignatures','timetable':'Horari','trash':'Paperera','stats':'Estadístiques','holidays':'Vacances','settings':'Configuració'}
    routes = {'dashboard':'dashboard','calendar':'calendar','homework':'items','exams':'items','events':'items','subjects':'subjects','timetable':'timetable','trash':'trash','stats':'stats','holidays':'holidays','settings':'settings'}

    def enhanced_base(title, body):
        # Manté l'estil original però afegeix les noves seccions al menú.
        menu = [x for x in mod.setting('menu', 'dashboard,calendar,homework,exams,events,subjects,timetable,stats,holidays,trash,settings').split(',') if x in labels]
        links=[]
        for x in menu:
            if x in ('homework','exams','events'):
                href=url_for('items', kind={'homework':'homework','exams':'exams','events':'events'}[x])
            else:
                href=url_for(routes[x])
            links.append(f'<a class="navitem" href="{href}">{labels[x]}</a>')
        nav=''.join(links)
        return mod.render_template_string('''<!doctype html><html lang="ca"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{title}} · Agenda</title><style>
:root{--p:#4f46e5;--bg:#f6f7fb;--card:#fff;--text:#172033;--muted:#667085;--ok:#16a34a;--danger:#dc2626;--line:#e5e7eb}*{box-sizing:border-box}body{margin:0;background:var(--bg);font-family:system-ui,-apple-system,Segoe UI,sans-serif;color:var(--text)}header{background:var(--card);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:5}.bar{max-width:1180px;margin:auto;padding:14px 18px;display:flex;gap:18px;align-items:center}.brand{font-weight:800;font-size:20px;color:var(--p);white-space:nowrap}.nav{display:flex;gap:7px;overflow:auto}.navitem{padding:8px 10px;border-radius:9px;color:var(--text);text-decoration:none;white-space:nowrap}.navitem:hover{background:#eef2ff}.logout{margin-left:auto}.wrap{max-width:1180px;margin:28px auto;padding:0 18px}h1{margin:0 0 18px;font-size:30px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px;box-shadow:0 3px 12px #00000008}.btn{display:inline-block;border:0;border-radius:10px;padding:10px 14px;background:var(--p);color:white;text-decoration:none;cursor:pointer}.btn.alt{background:#eef2ff;color:#3730a3}.btn.danger{background:var(--danger)}.btn.ok{background:var(--ok)}form{display:grid;gap:12px}input,textarea,select{width:100%;padding:11px;border:1px solid #d0d5dd;border-radius:10px;font:inherit;background:white}textarea{min-height:100px}label{font-weight:650}.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.muted{color:var(--muted)}.flash{padding:12px;border-radius:10px;background:#ecfdf3;margin-bottom:12px}.item{display:flex;justify-content:space-between;gap:15px;align-items:center;border-top:1px solid #eee;padding:13px 0}.badge{padding:4px 8px;border-radius:99px;background:#eef2ff;color:#3730a3;font-size:12px}.stats{font-size:28px;font-weight:800}.small{font-size:13px}.table{width:100%;border-collapse:collapse}.table th,.table td{padding:10px;border-bottom:1px solid var(--line);text-align:left}@media(max-width:700px){.navitem{font-size:13px}.wrap{margin-top:18px}.item{align-items:flex-start;flex-direction:column}.bar{gap:8px}}
</style></head><body><header><div class="bar"><div class="brand">📚 Agenda Virtual</div><nav class="nav">{{nav|safe}}</nav>{% if session.user_id %}<a class="navitem logout" href="{{url_for('logout')}}">Sortir</a>{% endif %}</div></header><main class="wrap">{% with messages=get_flashed_messages() %}{% for m in messages %}<div class="flash">{{m}}</div>{% endfor %}{% endwith %}{{body|safe}}</main></body></html>''', title=title, body=body, nav=nav)

    mod.base = enhanced_base

    @app.route('/estadistiques')
    @mod.login_required
    def stats():
        con=mod.db()
        counts={k:con.execute('SELECT COUNT(*) c FROM items WHERE kind=? AND trashed=0',(k,)).fetchone()['c'] for k in ('homework','exam','event')}
        done=con.execute("SELECT COUNT(*) c FROM items WHERE kind='homework' AND completed=1 AND trashed=0").fetchone()['c']
        trash=con.execute('SELECT COUNT(*) c FROM items WHERE trashed=1').fetchone()['c']
        subjects=con.execute('SELECT COUNT(*) c FROM subjects').fetchone()['c']
        con.close()
        return mod.base('Estadístiques',f'''<h1>📊 Estadístiques</h1><div class="grid"><div class="card"><div class="muted">Deures</div><div class="stats">{counts['homework']}</div></div><div class="card"><div class="muted">Deures acabats</div><div class="stats">{done}</div></div><div class="card"><div class="muted">Exàmens</div><div class="stats">{counts['exam']}</div></div><div class="card"><div class="muted">Esdeveniments</div><div class="stats">{counts['event']}</div></div><div class="card"><div class="muted">Assignatures</div><div class="stats">{subjects}</div></div><div class="card"><div class="muted">Paperera</div><div class="stats">{trash}</div></div></div>''')

    @app.route('/vacances', methods=['GET','POST'])
    @mod.login_required
    def holidays():
        con=mod.db()
        if request.method=='POST':
            action=request.form.get('action')
            if action=='add':
                d=request.form.get('holiday_date',''); name=request.form.get('name','').strip()
                if d and name:
                    con.execute('INSERT INTO holidays(holiday_date,name) VALUES(?,?)',(d,name)); con.commit(); flash('Vacança afegida.')
            elif action=='delete':
                con.execute('DELETE FROM holidays WHERE id=?',(request.form.get('id'),)); con.commit(); flash('Vacança eliminada.')
        rows=con.execute('SELECT * FROM holidays ORDER BY holiday_date').fetchall(); con.close()
        lis=''.join(f'<div class="item"><div><b>{r["name"]}</b><div class="muted">{r["holiday_date"]}</div></div><form method="post"><input type="hidden" name="action" value="delete"><input type="hidden" name="id" value="{r["id"]}"><button class="btn danger">Eliminar</button></form></div>' for r in rows) or '<p class="muted">No hi ha vacances manuals.</p>'
        return mod.base('Vacances',f'''<h1>🏖️ Vacances i dies lliures</h1><div class="card"><form method="post"><input type="hidden" name="action" value="add"><label>Data<input type="date" name="holiday_date" required></label><label>Nom<input name="name" placeholder="Vacances de Nadal" required></label><button class="btn">Afegir</button></form></div><div class="card" style="margin-top:16px">{lis}</div>''')

    # Substitueix la vista de configuració existent per una de més completa.
    def settings_plus():
        if request.method=='POST':
            mod.set_setting('trash_days',request.form.get('trash_days','30'))
            mod.set_setting('near_days',request.form.get('near_days','7'))
            mod.set_setting('backup_enabled','1' if request.form.get('backup_enabled') else '0')
            mod.set_setting('backup_hour',request.form.get('backup_hour','20'))
            menu=request.form.getlist('menu')
            mod.set_setting('menu',','.join(menu))
            flash('Configuració guardada.')
            return redirect(url_for('settings'))
        selected=set(mod.setting('menu','dashboard,calendar,homework,exams,events,subjects,timetable,stats,holidays,trash,settings').split(','))
        options=''.join(f'<label><input type="checkbox" name="menu" value="{k}" {"checked" if k in selected else ""}> {v}</label>' for k,v in labels.items())
        return mod.base('Configuració',f'''<h1>⚙️ Configuració</h1><div class="card"><form method="post"><label>Dies de conservació de la paperera<input type="number" min="1" name="trash_days" value="{mod.setting("trash_days","30")}"></label><label>Dies de "Proper"<input type="number" min="1" name="near_days" value="{mod.setting("near_days","7")}"></label><label><input type="checkbox" name="backup_enabled" {"checked" if mod.setting("backup_enabled","0")=="1" else ""}> Còpia automàtica diària</label><label>Hora de la còpia (0-23)<input type="number" min="0" max="23" name="backup_hour" value="{mod.setting("backup_hour","20")}"></label><h2>Menú superior</h2>{options}<button class="btn">Guardar</button></form></div><div class="card" style="margin-top:16px"><h2>💾 Dades</h2><div class="row"><a class="btn alt" href="{url_for("backup")}">Descarregar SQLite</a><a class="btn alt" href="{url_for("export_json")}">Exportar JSON</a><a class="btn alt" href="{url_for("import_json")}">Importar JSON</a></div></div>''')
    app.view_functions['settings']=mod.login_required(settings_plus)

    @app.route('/importar', methods=['GET','POST'])
    @mod.login_required
    def import_json():
        if request.method=='POST':
            raw=request.files.get('file')
            if not raw or not raw.filename:
                flash('Selecciona un fitxer JSON.')
                return redirect(url_for('import_json'))
            try:
                data=json.load(raw.stream); con=mod.db()
                for s in data.get('subjects',[]):
                    con.execute('INSERT OR IGNORE INTO subjects(id,name,color) VALUES(?,?,?)',(s.get('id'),s.get('name',''),s.get('color','#4f46e5')))
                for h in data.get('holidays',[]):
                    con.execute('INSERT INTO holidays(holiday_date,name) VALUES(?,?)',(h.get('holiday_date'),h.get('name','')))
                for t in data.get('timetable',[]):
                    con.execute('INSERT INTO timetable(weekday,start_time,end_time,subject_id,room) VALUES(?,?,?,?,?)',(t.get('weekday'),t.get('start_time'),t.get('end_time'),t.get('subject_id'),t.get('room','')))
                for i in data.get('items',[]):
                    con.execute('INSERT OR IGNORE INTO items(id,kind,title,description,event_date,event_time,place,subject_id,completed,trashed,deleted_at,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(i.get('id'),i.get('kind'),i.get('title',''),i.get('description',''),i.get('event_date'),i.get('event_time',''),i.get('place',''),i.get('subject_id'),i.get('completed',0),i.get('trashed',0),i.get('deleted_at'),i.get('created_at') or datetime.now().isoformat()))
                con.commit(); con.close(); flash('Importació completada.')
            except Exception as e:
                flash('No s’ha pogut importar el JSON: '+str(e))
            return redirect(url_for('import_json'))
        return mod.base('Importar', '<h1>📥 Importar dades</h1><div class="card"><form method="post" enctype="multipart/form-data"><label>Fitxer JSON<input type="file" name="file" accept="application/json,.json" required></label><button class="btn">Importar</button></form></div>')

    # Paperera: afegeix eliminació permanent.
    old_trash = app.view_functions.get('trash')
    def trash_plus():
        mod.clean_trash(); con=mod.db(); rows=con.execute('SELECT * FROM items WHERE trashed=1 ORDER BY deleted_at DESC').fetchall(); con.close()
        html='<h1>🗑️ Paperera</h1><div class="card">'
        if not rows: html+='<p class="muted">La paperera és buida.</p>'
        for r in rows:
            html+=f'''<div class="item"><div><b>{r['title']}</b><div class="muted small">Eliminat: {r['deleted_at']}</div></div><div class="row"><a class="btn alt" href="{url_for('restore_item',item_id=r['id'])}">Restaurar</a><form method="post" action="{url_for('permanent_delete',item_id=r['id'])}"><button class="btn danger">Eliminar definitivament</button></form></div></div>'''
        return mod.base('Paperera',html+'</div>')
    if old_trash: app.view_functions['trash']=mod.login_required(trash_plus)

    @app.route('/paperera/eliminar/<int:item_id>', methods=['POST'])
    @mod.login_required
    def permanent_delete(item_id):
        con=mod.db(); mod.delete_item_files(con,item_id); con.execute('DELETE FROM items WHERE id=? AND trashed=1',(item_id,)); con.commit(); con.close(); flash('Element eliminat definitivament.'); return redirect(url_for('trash'))

    @app.before_request
    def automatic_backup():
        if request.endpoint in ('static','login','logout') or not session_user(app): return
        if mod.setting('backup_enabled','0')!='1': return
        hour=int(mod.setting('backup_hour','20') or 20)
        now=datetime.now()
        if now.hour < hour: return
        last=mod.setting('last_backup','')
        if last == now.date().isoformat(): return
        name=f'agenda_auto_{now.strftime("%Y%m%d_%H%M%S")}.sqlite3'; target=os.path.join(mod.BACKUPS,name)
        src=sqlite3.connect(mod.DB); dst=sqlite3.connect(target); src.backup(dst); dst.close(); src.close(); mod.set_setting('last_backup',now.date().isoformat())


def session_user(app):
    from flask import session
    return session.get('user_id') is not None
