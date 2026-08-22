import os, sqlite3
from pathlib import Path
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE=Path(__file__).resolve().parent
DB=BASE/"angola_oportunidades.db"
UPLOADS=BASE/"static"/"uploads"; UPLOADS.mkdir(parents=True,exist_ok=True)
app=Flask(__name__); app.secret_key=os.environ.get("SECRET_KEY","CHANGE-ME")
app.config["MAX_CONTENT_LENGTH"]=5*1024*1024
ALLOWED={"jpg","jpeg","png","webp"}
CATEGORIES=["Empregos","Concursos","Bolsas de estudo","Cursos","Motas","Carros","Casas","Telefones","Hospedagem","Aluguer de carros","Aluguer de motas","Aluguer de salões de festas","Outros produtos"]
PROVINCES=["Luanda","Benguela","Huíla","Huambo","Namibe","Cabinda","Bié","Cunene","Cuando Cubango","Cuanza Norte","Cuanza Sul","Malanje","Moxico","Uíge","Zaire","Lunda Norte","Lunda Sul"]

def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init_db():
    c=db()
    c.executescript("""CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT,email TEXT UNIQUE,password TEXT,province TEXT,role TEXT DEFAULT 'user',active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS ads(id INTEGER PRIMARY KEY,title TEXT,description TEXT,category TEXT,province TEXT,price TEXT,image TEXT,user_id INTEGER,status TEXT DEFAULT 'pending',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS reports(id INTEGER PRIMARY KEY,ad_id INTEGER,reason TEXT,status TEXT DEFAULT 'open',created_at TEXT DEFAULT CURRENT_TIMESTAMP);""")
    if not c.execute("SELECT id FROM users WHERE email='admin@angolaoportunidades.ao'").fetchone():
        c.execute("INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)",("Administrador","admin@angolaoportunidades.ao",generate_password_hash("Admin@12345"),"admin"))
    admin=c.execute("SELECT id FROM users WHERE email='admin@angolaoportunidades.ao'").fetchone()["id"]
    demos=[("Hotel Exemplo — Quarto Standard","Quarto com Wi-Fi, estacionamento e pequeno-almoço.","Hospedagem","Luanda","45.000"),
           ("Toyota Corolla — Aluguer","Viatura para aluguer por dia.","Aluguer de carros","Luanda","55.000"),
           ("Honda CG — Aluguer","Mota disponível para aluguer diário.","Aluguer de motas","Huíla","20.000"),
           ("Salão Elegance — Eventos","Espaço para casamentos e festas.","Aluguer de salões de festas","Benguela","150.000")]
    for t,d,cat,p,pv in demos:
        if not c.execute("SELECT id FROM ads WHERE title=?",(t,)).fetchone():
            c.execute("INSERT INTO ads(title,description,category,province,price,user_id,status) VALUES(?,?,?,?,?,?,?)",(t,d,cat,p,pv,admin,"approved"))
    c.commit(); c.close()
def user():
    if "uid" not in session:return None
    c=db(); u=c.execute("SELECT * FROM users WHERE id=? AND active=1",(session["uid"],)).fetchone(); c.close(); return u
def admin_required(f):
    @wraps(f)
    def w(*a,**k):
        if not user() or user()["role"]!="admin": return redirect(url_for("login"))
        return f(*a,**k)
    return w
@app.context_processor
def ctx(): return {"current_user":user(),"categories":CATEGORIES,"provinces":PROVINCES}
@app.route("/")
def home():
    q=request.args.get("q",""); cat=request.args.get("category",""); prov=request.args.get("province","")
    c=db(); sql="SELECT ads.*,users.name user_name FROM ads LEFT JOIN users ON users.id=ads.user_id WHERE ads.status='approved'"; args=[]
    if q: sql+=" AND (ads.title LIKE ? OR ads.description LIKE ?)"; args += [f"%{q}%",f"%{q}%"]
    if cat: sql+=" AND ads.category=?"; args.append(cat)
    if prov: sql+=" AND ads.province=?"; args.append(prov)
    ads=c.execute(sql+" ORDER BY ads.id DESC",args).fetchall(); c.close()
    return render_template("home.html",ads=ads,q=q,category=cat,province=prov)
@app.route("/register",methods=["GET","POST"])
def register():
    if request.method=="POST":
        try:
            c=db(); c.execute("INSERT INTO users(name,email,password,province) VALUES(?,?,?,?)",(request.form["name"],request.form["email"].lower(),generate_password_hash(request.form["password"]),request.form.get("province",""))); c.commit(); c.close(); flash("Conta criada."); return redirect(url_for("login"))
        except sqlite3.IntegrityError: flash("Email já registado.")
    return render_template("register.html")
@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        c=db(); u=c.execute("SELECT * FROM users WHERE email=? AND active=1",(request.form["email"].lower(),)).fetchone(); c.close()
        if u and check_password_hash(u["password"],request.form["password"]):
            session["uid"]=u["id"]; return redirect(url_for("admin") if u["role"]=="admin" else url_for("home"))
        flash("Credenciais inválidas.")
    return render_template("login.html")
@app.route("/logout")
def logout(): session.clear(); return redirect(url_for("home"))
@app.route("/anunciar",methods=["GET","POST"])
def anunciar():
    if not user(): return redirect(url_for("login"))
    if request.method=="POST":
        f=request.files.get("image"); image=None
        if f and f.filename:
            ext=f.filename.rsplit(".",1)[-1].lower()
            if ext not in ALLOWED: flash("Formato de imagem inválido."); return redirect(url_for("anunciar"))
            image=secure_filename(f"{user()['id']}_{f.filename}"); f.save(UPLOADS/image)
        c=db(); c.execute("INSERT INTO ads(title,description,category,province,price,image,user_id) VALUES(?,?,?,?,?,?,?)",(request.form["title"],request.form["description"],request.form["category"],request.form["province"],request.form.get("price",""),image,user()["id"])); c.commit(); c.close(); flash("Anúncio enviado para aprovação."); return redirect(url_for("home"))
    return render_template("anunciar.html")
@app.route("/admin")
@admin_required
def admin():
    c=db(); stats={"total":c.execute("SELECT count(*) n FROM ads WHERE status='approved'").fetchone()["n"],"pending":c.execute("SELECT count(*) n FROM ads WHERE status='pending'").fetchone()["n"],"users":c.execute("SELECT count(*) n FROM users").fetchone()["n"],"reports":c.execute("SELECT count(*) n FROM reports WHERE status='open'").fetchone()["n"]}
    ads=c.execute("SELECT ads.*,users.name user_name FROM ads LEFT JOIN users ON users.id=ads.user_id ORDER BY ads.id DESC").fetchall(); users=c.execute("SELECT * FROM users ORDER BY id DESC").fetchall(); reports=c.execute("SELECT reports.*,ads.title FROM reports JOIN ads ON ads.id=reports.ad_id WHERE reports.status='open'").fetchall(); c.close()
    return render_template("admin.html",stats=stats,ads=ads,users=users,reports=reports)
@app.post("/admin/ad/<int:i>/<action>")
@admin_required
def modad(i,action):
    c=db()
    if action=="delete": c.execute("DELETE FROM ads WHERE id=?",(i,))
    elif action in ("approve","reject"): c.execute("UPDATE ads SET status=? WHERE id=?",(action+"d" if action=="approve" else "rejected",i))
    c.commit(); c.close(); return redirect(url_for("admin"))
@app.post("/admin/user/<int:i>/<action>")
@admin_required
def moduser(i,action):
    c=db(); c.execute("UPDATE users SET active=? WHERE id=?",(1 if action=="activate" else 0,i)); c.commit(); c.close(); return redirect(url_for("admin"))
if __name__=="__main__":
    init_db(); app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)))
