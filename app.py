import os, sqlite3, json, uuid
from datetime import datetime, date, timedelta
from functools import wraps
from flask import Flask, request, redirect, url_for, session, send_from_directory, render_template_string, flash, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, 'instance')
UPLOADS = os.path.join(BASE, 'uploads')
BACKUPS = os.path.join(BASE, 'backups')
DB = os.path.join(DATA, 'agenda.sqlite3')
os.makedirs(DATA, exist_ok=True); os.makedirs(UPLOADS, exist_ok=True); os.makedirs(BACKUPS, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'canvia-aquest-secret-en-produccio')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

SCHEMA = '''
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, password_hash TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS subjects (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, color TEXT DEFAULT '#4f46e5');
CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, title TEXT NOT NULL, description TEXT DEFAULT '', event_date TEXT NOT NULL, event_time TEXT DEFAULT '', place TEXT DEFAULT '', subject_id INTEGER, completed INTEGER DEFAULT 0, trashed INTEGER DEFAULT 0, deleted_at TEXT, created_at TEXT NOT NULL, FOREIGN KEY(subject_id) REFERENCES subjects(id));
CREATE TABLE IF NOT EXISTS attachments (id INTEGER PRIMARY KEY AUTOINCREMENT, item_id INTEGER NOT NULL, filename TEXT NOT NULL, original_name TEXT NOT NULL, FOREIGN KEY(item_id) REFERENCES items(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS timetable (id INTEGER PRIMARY KEY AUTOINCREMENT, weekday INTEGER NOT NULL, start_time TEXT NOT NULL, end_time TEXT NOT NULL, subject_id INTEGER, room TEXT DEFAULT '', FOREIGN KEY(subject_id) REFERENCES subjects(id));
CREATE TABLE IF NOT EXISTS holidays (id INTEGER PRIMARY KEY AUTOINCREMENT, holiday_date TEXT NOT NULL, name TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_items_date ON items(event_date);
'''

def db():
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; con.execute('PRAGMA foreign_keys=ON'); return con

def init_db():
    con=db(); con.executescript(SCHEMA)
    if con.execute('SELECT COUNT(*) FROM settings').fetchone()[0] == 0:
        defaults={'trash_days':'30','near_days':'7','menu':'dashboard,calendar,homework,exams,events,subjects,timetable,trash,settings'}
        con.executemany('INSERT INTO settings(key,value) VALUES(?,?)', defaults.items())
    con.commit(); con.close()
init_db()

def setting(k, default=''):
    con=db(); r=con.execute('SELECT value FROM settings WHERE key=?',(k,)).fetchone(); con.close(); return r['value'] if r else default

def set_setting(k,v):
    con=db(); con.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(k,v)); con.commit(); con.close()

def login_required(f):
    @wraps(f)
    def w(*a,**kw):
        if session.get('user_id') is None: return redirect(url_for('login'))
        return f(*a,**kw)
    return w

def delete_item_files(con,item_id):
    for a in con.execute('SELECT filename FROM attachments WHERE item_id=?',(item_id,)).fetchall():
        try: os.remove(os.path.join(UPLOADS,a['filename']))
        except FileNotFoundError: pass
    con.execute('DELETE FROM attachments WHERE item_id=?',(item_id,))

def clean_trash():
    days=int(setting('trash_days','30') or 30); cutoff=(datetime.now()-timedelta(days=days)).isoformat(); con=db()
    rows=con.execute('SELECT id FROM items WHERE trashed=1 AND deleted_at<?',(cutoff,)).fetchall()
    for r in rows: delete_item_files(con,r['id'])
    con.execute('DELETE FROM items WHERE trashed=1 AND deleted_at<?',(cutoff,)); con.commit(); con.close()

def base(title, body):
    labels={'dashboard':'Inici','calendar':'Calendari','homework':'Deures','exams':'Exàmens','events':'Esdeveniments','subjects':'Assignatures','timetable':'Horari','trash':'Paperera','settings':'Configuració'}
    routes={'dashboard':'dashboard','calendar':'calendar','homework':'items','exams':'items','events':'items','subjects':'subjects','timetable':'timetable','trash':'trash','settings':'settings'}
    menu=[x for x in setting('menu').split(',') if x in labels]
    nav=''.join(f'<a class="navitem" href="{url_for(routes[x], **({"kind":"homework"} if x=="homework" else {"kind":"exams"} if x=="exams" else {"kind":"events"} if x=="events" else {}))}">{labels[x]}</a>' for x in menu)
    return render_template_string('''<!doctype html><html lang="ca"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{title}} · Agenda</title><style>
:root{--p:#4f46e5;--bg:#f6f7fb;--card:#fff;--text:#172033;--muted:#667085;--ok:#16a34a;--danger:#dc2626}*{box-sizing:border-box}body{margin:0;background:var(--bg);font-family:system-ui,-apple-system,Segoe UI,sans-serif;color:var(--text)}header{background:var(--card);border-bottom:1px solid #e5e7eb;position:sticky;top:0;z-index:5}.bar{max-width:1180px;margin:auto;padding:14px 18px;display:flex;gap:18px;align-items:center}.brand{font-weight:800;font-size:20px;color:var(--p);white-space:nowrap}.nav{display:flex;gap:7px;overflow:auto}.navitem{padding:8px 10px;border-radius:9px;color:var(--text);text-decoration:none;white-space:nowrap}.navitem:hover{background:#eef2ff}.logout{margin-left:auto}.wrap{max-width:1180px;margin:28px auto;padding:0 18px}h1{margin:0 0 18px;font-size:30px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}.card{background:var(--card);border:1px solid #e5e7eb;border-radius:16px;padding:18px;box-shadow:0 3px 12px #00000008}.btn{display:inline-block;border:0;border-radius:10px;padding:10px 14px;background:var(--p);color:white;text-decoration:none;cursor:pointer}.btn.alt{background:#eef2ff;color:#3730a3}.btn.danger{background:var(--danger)}.btn.ok{background:var(--ok)}form{display:grid;gap:12px}input,textarea,select{width:100%;padding:11px;border:1px solid #d0d5dd;border-radius:10px;font:inherit;background:white}textarea{min-height:100px}label{font-weight:650}.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.muted{color:var(--muted)}.flash{padding:12px;border-radius:10px;background:#ecfdf3;margin-bottom:12px}.item{display:flex;justify-content:space-between;gap:15px;align-items:center;border-top:1px solid #eee;padding:13px 0}.badge{padding:4px 8px;border-radius:99px;background:#eef2ff;color:#3730a3;font-size:12px}.calendar{display:grid;grid-template-columns:repeat(7,1fr);gap:6px}.day{min-height:115px;background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:8px}.today{outline:2px solid var(--p)}.event{font-size:12px;padding:4px 6px;border-radius:6px;background:#eef2ff;margin-top:5px;overflow:hidden}.stats{font-size:28px;font-weight:800}.small{font-size:13px}@media(max-width:700px){.navitem{font-size:13px}.wrap{margin-top:18px}.day{min-height:90px;padding:5px}}
</style></head><body><header><div class="bar"><div class="brand">📚 Agenda Virtual</div><nav class="nav">{{nav|safe}}</nav>{% if session.user_id %}<a class="navitem logout" href="{{url_for('logout')}}">Sortir</a>{% endif %}</div></header><main class="wrap">{% with messages=get_flashed_messages() %}{% for m in messages %}<div class="flash">{{m}}</div>{% endfor %}{% endwith %}{{body|safe}}</main></body></html>''',title=title,body=body,nav=nav)

def setup_form(): return '<form method="post"><label>Nova contrasenya<input type="password" name="password" required minlength="6"></label><button class="btn">Crear agenda</button></form>'

@app.route('/login',methods=['GET','POST'])
def login():
    con=db(); user=con.execute('SELECT * FROM users LIMIT 1').fetchone(); con.close()
    if not user:
        if request.method=='POST':
            p=request.form.get('password','')
            if len(p)<6: return base('Configuració inicial','<div class="card"><h1>Configura la contrasenya</h1><p>La contrasenya ha de tenir almenys 6 caràcters.</p>'+setup_form()+'</div>')
            con=db(); con.execute('INSERT INTO users(password_hash,created_at) VALUES(?,?)',(generate_password_hash(p),datetime.now().isoformat())); con.commit(); uid=con.execute('SELECT id FROM users').fetchone()['id']; con.close(); session['user_id']=uid; return redirect(url_for('dashboard'))
        return base('Configuració inicial','<div class="card" style="max-width:520px;margin:auto"><h1>📚 Primera configuració</h1><p>Crea la contrasenya de la teva agenda. Només es guarda el hash.</p>'+setup_form()+'</div>')
    if request.method=='POST':
        if check_password_hash(user['password_hash'],request.form.get('password','')): session['user_id']=user['id']; return redirect(url_for('dashboard'))
        flash('Contrasenya incorrecta.')
    return base('Entrar','<div class="card" style="max-width:460px;margin:auto"><h1>Entrar</h1><form method="post"><label>Contrasenya<input type="password" name="password" required autofocus></label><button class="btn">Entrar</button></form></div>')

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    clean_trash(); con=db(); today=date.today().isoformat(); end=(date.today()+timedelta(days=int(setting('near_days','7')))).isoformat()
    pending=con.execute('SELECT COUNT(*) c FROM items WHERE trashed=0 AND completed=0 AND event_date>=?',(today,)).fetchone()['c']
    exams=con.execute("SELECT COUNT(*) c FROM items WHERE kind='exam' AND trashed=0 AND event_date>=?",(today,)).fetchone()['c']
    done=con.execute("SELECT COUNT(*) c FROM items WHERE kind='homework' AND completed=1 AND trashed=0").fetchone()['c']
    upcoming=con.execute('SELECT * FROM items WHERE trashed=0 AND event_date BETWEEN ? AND ? ORDER BY event_date,event_time LIMIT 8',(today,end)).fetchall(); con.close()
    rows=''.join(f'<div class="item"><div><b>{r["title"]}</b><div class="muted small">{r["event_date"]} {r["event_time"] or ""} · {r["place"] or "Sense lloc"}</div></div><a class="btn alt" href="{url_for("edit_item",item_id=r["id"])}">Obrir</a></div>' for r in upcoming) or '<p class="muted">No tens res proper. 🎉</p>'
    return base('Inici',f'<h1>Bon dia! 👋</h1><div class="grid"><div class="card"><div class="muted">Pendents</div><div class="stats">{pending}</div></div><div class="card"><div class="muted">Exàmens propers</div><div class="stats">{exams}</div></div><div class="card"><div class="muted">Deures acabats</div><div class="stats">{done}</div></div></div><div class="card" style="margin-top:16px"><h2>📌 Proper</h2>{rows}</div>')

@app.route('/<kind>')
@login_required
def items(kind):
    if kind not in ('homework','exams','events'): return redirect(url_for('dashboard'))
    real={'homework':'homework','exams':'exam','events':'event'}[kind]; title={'homework':'Deures','exams':'Exàmens','events':'Esdeveniments'}[kind]
    con=db(); rows=con.execute('SELECT items.*,subjects.name subject FROM items LEFT JOIN subjects ON subjects.id=items.subject_id WHERE items.kind=? AND items.trashed=0 ORDER BY event_date,event_time',(real,)).fetchall(); con.close()
    html=f'<div class="row" style="justify-content:space-between"><h1>{title}</h1><a class="btn" href="{url_for("new_item",kind=real)}">＋ Afegir</a></div><div class="card">'
    if not rows: html+='<p class="muted">Encara no hi ha elements.</p>'
    for r in rows:
        complete='<div>✅ Completat</div>' if r['completed'] else ''
        complete_btn='' if r['completed'] else f'<a class="btn ok" href="{url_for("complete_item",item_id=r["id"])}">Acabar</a>' if real=='homework' else ''
        html+=f'<div class="item"><div><b>{r["title"]}</b> <span class="badge">{r["subject"] or r["kind"]}</span><div class="muted small">{r["event_date"]} {r["event_time"] or ""} · {r["place"] or "Sense lloc"}</div>{complete}</div><div class="row">{complete_btn}<a class="btn alt" href="{url_for("edit_item",item_id=r["id"])}">Editar</a><a class="btn danger" href="{url_for("trash_item",item_id=r["id"])}">Paperera</a></div></div>'
    return base(title,html+'</div>')

def item_form(kind,item=None):
    con=db(); subs=con.execute('SELECT * FROM subjects ORDER BY name').fetchall(); con.close(); i=item or {}
    title={'homework':'Nou deure','exam':'Nou examen','event':'Nou esdeveniment'}[kind]
    return base(title,render_template_string('''<div class="card"><h1>{{title}}</h1><form method="post" enctype="multipart/form-data"><label>Títol<input name="title" required value="{{i.title or ''}}"></label><label>Descripció<textarea name="description">{{i.description or ''}}</textarea></label><div class="grid"><label>Data<input type="date" name="event_date" required value="{{i.event_date or date}}"></label><label>Hora<input type="time" name="event_time" value="{{i.event_time or ''}}"></label><label>Lloc<input name="place" value="{{i.place or ''}}"></label></div>{% if kind!='event' %}<label>Assignatura<select name="subject_id"><option value="">—</option>{% for s in subs %}<option value="{{s.id}}" {% if i.subject_id==s.id %}selected{% endif %}>{{s.name}}</option>{% endfor %}</select></label>{% endif %}<label>Fitxer o imatge<input type="file" name="attachment"></label><div class="row"><button class="btn">Guardar</button><a class="btn alt" href="{{url_for('items',kind=kind)}}">Cancel·lar</a></div></form></div>''',title=title,i=i,subs=subs,kind=kind,date=date.today().isoformat()))

@app.route('/nou/<kind>',methods=['GET','POST'])
@login_required
def new_item(kind):
    if kind not in ('homework','exam','event'): return redirect(url_for('dashboard'))
    if request.method=='POST': return save_item(kind)
    return item_form(kind)

def save_item(kind,item_id=None):
    title=request.form.get('title','').strip(); event_date=request.form.get('event_date',''); description=request.form.get('description',''); event_time=request.form.get('event_time',''); place=request.form.get('place',''); subject_id=request.form.get('subject_id') or None
    if not title or not event_date: flash('Falten dades obligatòries.'); return item_form(kind)
    con=db(); now=datetime.now().isoformat()
    if item_id:
        con.execute('UPDATE items SET title=?,description=?,event_date=?,event_time=?,place=?,subject_id=? WHERE id=?',(title,description,event_date,event_time,place,subject_id,item_id))
    else:
        cur=con.execute('INSERT INTO items(kind,title,description,event_date,event_time,place,subject_id,created_at) VALUES(?,?,?,?,?,?,?,?)',(kind,title,description,event_date,event_time,place,subject_id,now)); item_id=cur.lastrowid
    f=request.files.get('attachment')
    if f and f.filename:
        original=secure_filename(f.filename); filename=f'{uuid.uuid4().hex}_{original}'; f.save(os.path.join(UPLOADS,filename)); con.execute('INSERT INTO attachments(item_id,filename,original_name) VALUES(?,?,?)',(item_id,filename,original))
    con.commit(); con.close(); flash('Guardat correctament.'); return redirect(url_for('items',kind={'homework':'homework','exam':'exams','event':'events'}[kind]))

@app.route('/editar/<int:item_id>',methods=['GET','POST'])
@login_required
def edit_item(item_id):
    con=db(); item=con.execute('SELECT * FROM items WHERE id=?',(item_id,)).fetchone(); con.close()
    if not item: return redirect(url_for('dashboard'))
    if request.method=='POST': return save_item(item['kind'],item_id)
    return item_form(item['kind'],item)

@app.route('/acabar/<int:item_id>')
@login_required
def complete_item(item_id):
    con=db(); r=con.execute('SELECT * FROM items WHERE id=?',(item_id,)).fetchone()
    if r and r['kind']=='homework':
        delete_item_files(con,item_id); con.execute('UPDATE items SET completed=1 WHERE id=?',(item_id,)); con.commit(); flash('Deure marcat com acabat. Els seus adjunts s’han eliminat.')
    con.close(); return redirect(url_for('items',kind='homework'))

@app.route('/paperera/<int:item_id>')
@login_required
def trash_item(item_id):
    con=db(); con.execute('UPDATE items SET trashed=1,deleted_at=? WHERE id=?',(datetime.now().isoformat(),item_id)); con.commit(); con.close(); flash('Element enviat a la paperera.'); return redirect(request.referrer or url_for('dashboard'))

@app.route('/paperera')
@login_required
def trash():
    clean_trash(); con=db(); rows=con.execute('SELECT * FROM items WHERE trashed=1 ORDER BY deleted_at DESC').fetchall(); con.close()
    html='<h1>🗑️ Paperera</h1><div class="card">'
    if not rows: html+='<p class="muted">La paperera és buida.</p>'
    for r in rows: html+=f'<div class="item"><div><b>{r["title"]}</b><div class="muted small">Eliminat: {r["deleted_at"]}</div></div><a class="btn alt" href="{url_for("restore_item",item_id=r["id"])}">Restaurar</a></div>'
    return base('Paperera',html+'</div>')

@app.route('/restaurar/<int:item_id>')
@login_required
def restore_item(item_id):
    con=db(); con.execute('UPDATE items SET trashed=0,deleted_at=NULL WHERE id=?',(item_id,)); con.commit(); con.close(); return redirect(url_for('trash'))

@app.route('/calendari')
@login_required
def calendar():
    today=date.today(); y=int(request.args.get('year',today.year)); m=int(request.args.get('month',today.month)); first=date(y,m,1); nextm=date(y+1,1,1) if m==12 else date(y,m+1,1); last=nextm-timedelta(days=1); start=first-timedelta(days=first.weekday()); end=last+timedelta(days=6-last.weekday())
    con=db(); rows=con.execute('SELECT * FROM items WHERE trashed=0 AND event_date>=? AND event_date<=? ORDER BY event_time',(start.isoformat(),end.isoformat())).fetchall(); con.close(); by={}
    for r in rows: by.setdefault(r['event_date'],[]).append(r)
    cells=[]; d=start
    while d<=end:
        ev=''.join(f'<div class="event">{r["title"]}</div>' for r in by.get(d.isoformat(),[])); cls='day today' if d==today else 'day'; cells.append(f'<div class="{cls}"><strong>{d.day}</strong>{ev}</div>'); d+=timedelta(days=1)
    prev=first-timedelta(days=1); nxt=nextm; return base('Calendari',f'<div class="row"><a class="btn alt" href="{url_for("calendar",year=prev.year,month=prev.month)}">←</a><h1>{y}-{m:02d}</h1><a class="btn alt" href="{url_for("calendar",year=nxt.year,month=nxt.month)}">→</a></div><div class="calendar">{"".join(cells)}</div>')

@app.route('/assignatures',methods=['GET','POST'])
@login_required
def subjects():
    con=db()
    if request.method=='POST' and request.form.get('name','').strip(): con.execute('INSERT INTO subjects(name,color) VALUES(?,?)',(request.form['name'].strip(),request.form.get('color','#4f46e5'))); con.commit()
    rows=con.execute('SELECT * FROM subjects ORDER BY name').fetchall(); con.close(); html='<h1>Assignatures</h1><div class="card"><form method="post"><input name="name" placeholder="Nom de l’assignatura" required><input type="color" name="color" value="#4f46e5"><button class="btn">Afegir</button></form></div><div class="card" style="margin-top:16px">'+''.join(f'<div class="item"><b>{r["name"]}</b></div>' for r in rows)+'</div>'; return base('Assignatures',html)

@app.route('/horari')
@login_required
def timetable():
    con=db(); rows=con.execute('SELECT timetable.*,subjects.name subject FROM timetable LEFT JOIN subjects ON subjects.id=timetable.subject_id ORDER BY weekday,start_time').fetchall(); con.close(); html='<h1>Horari</h1><div class="card">'+(''.join(f'<div class="item"><b>{r["subject"] or "Sense assignatura"}</b><span>{r["start_time"]}-{r["end_time"]} · {r["room"]}</span></div>' for r in rows) or '<p class="muted">Encara no hi ha classes.</p>')+'</div>'; return base('Horari',html)

@app.route('/configuracio',methods=['GET','POST'])
@login_required
def settings():
    if request.method=='POST':
        set_setting('trash_days',request.form.get('trash_days','30')); set_setting('near_days',request.form.get('near_days','7')); flash('Configuració guardada.'); return redirect(url_for('settings'))
    html=f'<h1>Configuració</h1><div class="card"><form method="post"><label>Dies de conservació de la paperera<input type="number" min="1" name="trash_days" value="{setting("trash_days","30")}"></label><label>Dies de "Proper"<input type="number" min="1" name="near_days" value="{setting("near_days","7")}"></label><button class="btn">Guardar</button></form></div><div class="card" style="margin-top:16px"><h2>Còpia de seguretat</h2><a class="btn alt" href="{url_for("backup")}">Descarregar SQLite</a><a class="btn alt" href="{url_for("export_json")}">Exportar JSON</a></div>'; return base('Configuració',html)

@app.route('/backup')
@login_required
def backup():
    name=f'agenda_{datetime.now().strftime("%Y%m%d_%H%M%S")}.sqlite3'; target=os.path.join(BACKUPS,name)
    src=sqlite3.connect(DB); dst=sqlite3.connect(target); src.backup(dst); dst.close(); src.close(); return send_file(target,as_attachment=True,download_name=name)

@app.route('/export.json')
@login_required
def export_json():
    con=db(); data={}
    for table in ('settings','subjects','items','attachments','timetable','holidays'): data[table]=[dict(r) for r in con.execute(f'SELECT * FROM {table}').fetchall()]
    con.close(); return app.response_class(json.dumps(data,ensure_ascii=False,indent=2),mimetype='application/json',headers={'Content-Disposition':'attachment; filename=agenda-export.json'})

@app.route('/uploads/<path:filename>')
@login_required
def uploaded(filename): return send_from_directory(UPLOADS,filename)

if __name__=='__main__': app.run(host='0.0.0.0',port=5000,debug=True)
