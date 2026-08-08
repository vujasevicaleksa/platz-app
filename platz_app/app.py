import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3

app = Flask(__name__)
app.secret_key = 'tajni_kl='+str(os.urandom(24))

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ADMIN_USER = "admin"
ADMIN_PASS = "petrolista123"

def init_db():
    conn = sqlite3.connect('baza.db')
    cursor = conn.cursor()
    # Tabela za vozila sa naslovnom slikom i detaljnim opisom
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vozila (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            naziv TEXT NOT NULL,
            godiste TEXT NOT NULL,
            kilometraza TEXT NOT NULL,
            motor TEXT NOT NULL,
            cijena TEXT NOT NULL,
            naslovna_slika TEXT NOT NULL,
            detaljni_opis TEXT
        )
    ''')
    # Tabela za dodatne slike galerije za svaki auto
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS slike (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vozilo_id INTEGER,
            slika_path TEXT NOT NULL,
            FOREIGN KEY (vozilo_id) REFERENCES vozila (id)
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('platz.html')

# Ruta za brisanje oglasa
@app.route('/admin/obrisi/<int:id>')
def obrisi_oglas(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    conn = sqlite3.connect('baza.db')
    cursor = conn.cursor()
    
    # Opciono: Možeš obrisati i fajlove slika sa hard diska, ali za početak je dovoljno iz baze:
    cursor.execute("DELETE FROM slike WHERE vozilo_id = ?", (id,))
    cursor.execute("DELETE FROM vozila WHERE id = ?", (id,))
    
    conn.commit()
    conn.close()
    
    return redirect(url_for('admin_panel'))

@app.route('/api/oglasi')
def api_oglasi():
    conn = sqlite3.connect('baza.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vozila ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

# Stranica za pojedinačni oglas i galeriju
@app.route('/oglas/<int:id>')
def detalji_oglasa(id):
    conn = sqlite3.connect('baza.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM vozila WHERE id = ?", (id,))
    auto = cursor.fetchone()
    
    cursor.execute("SELECT slika_path FROM slike WHERE vozilo_id = ?", (id,))
    slike = cursor.fetchall()
    
    conn.close()
    
    if not auto:
        return "Oglas ne postoji", 404
        
    return render_template('detalji.html', auto=dict(auto), slike=[s['slika_path'] for s in slike])

@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USER and request.form['password'] == ADMIN_PASS:
            session['logged_in'] = True
            return redirect(url_for('admin_panel'))
        else:
            return "Pogrešni podaci! <a href='/admin/login'>Nazad</a>"
    return '''
        <!DOCTYPE html>
        <html lang="sr"><head><meta charset="UTF-8"><title>Admin Login</title></head>
        <body style="background:#f8e110; font-family:sans-serif; display:flex; justify-content:center; align-items:center; height:100vh;">
            <form method="POST" style="background:white; padding:30px; border:4px solid black; box-shadow:8px 8px 0px black;">
                <h2>Admin Login</h2><br>
                <input type="text" name="username" placeholder="Korisničko ime" required style="padding:10px; margin-bottom:10px; width:100%; border:2px solid black;"><br>
                <input type="password" name="password" placeholder="Lozinka" required style="padding:10px; margin-bottom:15px; width:100%; border:2px solid black;"><br>
                <button type="submit" style="background:black; color:#f8e110; padding:10px 20px; font-weight:bold; border:none; width:100%; cursor:pointer;">Prijavi se</button>
            </form>
        </body></html>
    '''

@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        naziv = request.form['naziv']
        godiste = request.form['godiste']
        kilometraza = request.form['kilometraza']
        motor = request.form['motor']
        cijena = request.form['cijena']
        detaljni_opis = request.form['detaljni_opis']
        
        # Snimanje naslovne slike
        naslovna = request.files['naslovna_slika']
        naslovna_path = ""
        if naslovna:
            filename = naslovna.filename
            naslovna.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            naslovna_path = f"static/uploads/{filename}"

        conn = sqlite3.connect('baza.db')
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO vozila (naziv, godiste, kilometraza, motor, cijena, naslovna_slika, detaljni_opis) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (naziv, godiste, kilometraza, motor, cijena, naslovna_path, detaljni_opis))
        
        vozilo_id = cursor.lastrowid

        # Snimanje dodatnih slika za galeriju
        dodatne_slike = request.files.getlist('dodatne_slike')
        for slika in dodatne_slike:
            if slika and slika.filename != '':
                s_name = slika.filename
                slika.save(os.path.join(app.config['UPLOAD_FOLDER'], s_name))
                s_path = f"static/uploads/{s_name}"
                cursor.execute("INSERT INTO slike (vozilo_id, slika_path) VALUES (?, ?)", (vozilo_id, s_path))

        conn.commit()
        conn.close()
        return redirect(url_for('admin_panel'))

    return render_template('admin.html')

@app.route('/admin/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)