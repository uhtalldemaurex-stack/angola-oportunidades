import os, sqlite3
from functools import wraps
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE=Path(__file__).resolve().parent
DB=BASE/"angola_oportunidades.db"
UPLOADS=BASE/"static"/"uploads"; UPLOADS.mkdir(parents=True,exist_ok=True)
app=Flask(__name__)
app.secret_key=os.environ.get("SECRET_KEY","CHANGE-ME-IN-PRODUCTION")
app.config["MAX_CONTENT_LENGTH"]=5*1024*1024
CATEGORIES=["Empregos","Concursos","Bolsas de estudo","Cursos","Hospedagem","Arrendamento de carros","Arrendamento de motas","Motas","Carros","Casas","Telefones","Outros produtos"]
PROVINCES=["Luanda","Huíla","Namibe","Benguela","Huambo","Cabinda","Bié","Cunene","Cuando Cubango","Cuanza Norte","Cuanza Sul","Lunda Norte","Lunda Sul","Malanje","Moxico","Uíge","Zaire"]

def getdb():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init_db():
    c=getdb()
    c.executescript("""CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,email TEXT UNIQUE,password_hash TEXT,province TEXT,role TEXT DEFAULT 'user',active INTEGER DEFAULT 1,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS ads(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT,description TEXT,category TEXT,province TEXT,price TEXT,image TEXT,user_id INTEGER,status TEXT DEFAULT 'pending',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS reports(id INTEGER PRIMARY KEY AUTOINCREMENT,ad_id INTEGER,reason TEXT,status TEXT DEFAULT 'open',created_at TEXT DEFAULT CURRENT_TIMESTAMP);""")
    if not c.execute("SELECT id FROM users WHERE email=?",("admin@angolaoportunidades.ao",)).fetchone():
        c.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",("Administrador","admin@angolaoportunidades.ao",generate_password_hash("Admin@12345"),"admin"))
    admin=c.execute("SELECT id FROM users WHERE email=?",("admin@angolaoportunidades.ao",)).fetchone()["id"]
    demos=[
      ("Hotel Exemplo — Quarto Standard","Quarto com Wi-Fi, estacionamento e pequeno-almoço.","Hospedagem","Luanda","45.000/noite"),
      ("Toyota Corolla — Arrendamento","Viatura disponível para arrendamento.","Arrendamento de carros","Luanda","35.000/dia"),
      ("Honda CG — Arrendamento","Mota disponível para arrendamento.","Arrendamento de motas","Huíla","15.000/dia")]
    for title,desc,cat,prov,price in demos:
        if not c.execute("SELECT id FROM ads WHERE title=?",(title,)).fetchone():
            c.execute("INSERT INTO ads(title,description,category,province,price,user_id,status) VALUES(?,?,?,?,?,?,?)",(title,desc,cat,prov,price,admin,"approved"))
    c.commit(); c.close()

def user():
    uid=session.get("uid")
    if not uid:return None
    c=getdb(); u=c.execute("SELECT * FROM users WHERE id=? AND active=1",(uid,)).fetchone(); c.close(); return u
def required(fn):
    @wraps(fn)
    def w(*a,**kw):
        return fn(*a,**kw) if user() else redirect(url_for("login"))
    return w
def admin(fn):
    @wraps(fn)
    def w(*a,**kw):
        u=user()
        return fn(*a,**kw) if u and u["role"]=="admin" else redirect(url_for("login"))
    return w
@app.context_processor
def ctx(): return {"current_user":user(),"categories":CATEGORIES,"provinces":PROVINCES}

@app.route("/")
def home():
    q=request.args.get("q","").strip(); cat=request.args.get("category",""); prov=request.args.get("province","")
    c=getdb(); sql="SELECT ads.*,users.name user_name FROM ads LEFT JOIN users ON users.id=ads.user_id WHERE ads.status='approved'"; args=[]
    if q: sql+=" AND (ads.title LIKE ? OR ads.description LIKE ?)"; args += [f"%{q}%",f"%{q}%"]
    if cat: sql+=" AND ads.category=?"; args.append(cat)
    if prov: sql+=" AND ads.province=?"; args.append(prov)
    sql+=" ORDER BY ads.id DESC"; ads=c.execute(sql,args).fetchall(); c.close()
    return render_template("home.html",ads=ads,q=q,category=cat,province=prov)

@app.route("/register",methods=["GET","POST"])
def register():
    if request.method=="POST":
        name=request.form["name"].strip(); email=request.form["email"].strip().lower(); pw=request.form["password"]; prov=request.form.get("province","")
        if len(pw)<8: flash("A palavra-passe deve ter pelo menos 8 caracteres."); return redirect(url_for("register"))
        c=getdb()
        try:
            c.execute("INSERT INTO users(name,email,password_hash,province) VALUES(?,?,?,?)",(name,email,generate_password_hash(pw),prov)); c.commit()
            flash("Conta criada com sucesso."); return redirect(url_for("login"))
        except sqlite3.IntegrityError: flash("Este email já está registado.")
        finally:c.close()
    return render_template("register.html")

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        c=getdb(); u=c.execute("SELECT * FROM users WHERE email=? AND active=1",(request.form["email"].lower(),)).fetchone(); c.close()
        if u and check_password_hash(u["password_hash"],request.form["password"]):
            session.clear(); session["uid"]=u["id"]; return redirect(url_for("admin") if u["role"]=="admin" else url_for("home"))
        flash("Email ou palavra-passe inválidos.")
    return render_template("login.html")
@app.route("/logout")
def logout(): session.clear(); return redirect(url_for("home"))

@app.route("/anunciar",methods=["GET","POST"])
@required
def anunciar():
    if request.method=="POST":
        image=None; f=request.files.get("image")
        if f and f.filename:
            ext=f.filename.rsplit(".",1)[-1].lower() if "." in f.filename else ""
            if ext not in {"jpg","jpeg","png","webp"}: flash("Imagem inválida."); return redirect(url_for("anunciar"))
            image=secure_filename(f"{user()['id']}_{f.filename}"); f.save(UPLOADS/image)
        c=getdb(); c.execute("INSERT INTO ads(title,description,category,province,price,image,user_id,status) VALUES(?,?,?,?,?,?,?,'pending')",(request.form["title"],request.form["description"],request.form["category"],request.form["province"],request.form.get("price",""),image,user()["id"])); c.commit(); c.close()
        flash("Anúncio enviado para aprovação."); return redirect(url_for("home"))
    return render_template("anunciar.html")

@app.route("/admin")
@admin
def admin():
    c=getdb()
    stats={k:c.execute(sql).fetchone()[0] for k,sql in {"total":"SELECT COUNT(*) FROM ads WHERE status='approved'","pending":"SELECT COUNT(*) FROM ads WHERE status='pending'","users":"SELECT COUNT(*) FROM users","reports":"SELECT COUNT(*) FROM reports WHERE status='open'"}.items()}
    ads=c.execute("SELECT ads.*,users.name user_name FROM ads LEFT JOIN users ON users.id=ads.user_id ORDER BY ads.id DESC").fetchall()
    users=c.execute("SELECT * FROM users ORDER BY id DESC").fetchall()
    reports=c.execute("SELECT reports.*,ads.title FROM reports JOIN ads ON ads.id=reports.ad_id WHERE reports.status='open' ORDER BY reports.id DESC").fetchall(); c.close()
    return render_template("admin.html",stats=stats,ads=ads,users=users,reports=reports)

@app.post("/admin/ad/<int:aid>/<action>")
@admin
def mod_ad(aid,action):
    c=getdb()
    if action=="delete": c.execute("DELETE FROM ads WHERE id=?",(aid,))
    elif action in ("approve","reject"): c.execute("UPDATE ads SET status=? WHERE id=?",(action+"d" if action=="approve" else "rejected",aid))
    c.commit(); c.close(); return redirect(url_for("admin"))
@app.post("/admin/user/<int:uid>/<action>")
@admin
def mod_user(uid,action):
    c=getdb(); c.execute("UPDATE users SET active=? WHERE id=?",(1 if action=="activate" else 0,uid)); c.commit(); c.close(); return redirect(url_for("admin"))
@app.post("/admin/report/<int:rid>/resolve")
@admin
def resolve(rid):
    c=getdb(); c.execute("UPDATE reports SET status='resolved' WHERE id=?",(rid,)); c.commit(); c.close(); return redirect(url_for("admin"))

if __name__=="__main__":
    init_db(); app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)))
