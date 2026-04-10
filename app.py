from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os # <-- 1. AGREGÁ ESTA LÍNEA ARRIBA DE TODO

app = Flask(__name__)

# CONFIGURACIÓN DE BASE DE DATOS (SQLite)
# 2. CAMBIÁ TODA ESTA PARTE:
if os.environ.get('VERCEL'):
    # Si estamos en Vercel, usamos la carpeta temporal
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/templo.db'
else:
    # Si estás en tu PC (Local), sigue como antes
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///templo.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# MODELO DE LA BASE DE DATOS
class Socio(db.Model):
    dni = db.Column(db.String(20), primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    plan = db.Column(db.String(50))
    vence = db.Column(db.String(50))
    # Rutinas por día (guardamos texto simple)
    rutina_lunes = db.Column(db.Text, default="")
    rutina_martes = db.Column(db.Text, default="")
    rutina_miercoles = db.Column(db.Text, default="")
    rutina_jueves = db.Column(db.Text, default="")
    rutina_viernes = db.Column(db.Text, default="")

# CREAR LA BASE DE DATOS SI NO EXISTE
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        dni = request.form.get('dni')
        password = request.form.get('password')
        if dni == "0000": return redirect(url_for('admin_panel'))
        
        socio = Socio.query.get(dni)
        if socio and socio.password == password:
            return redirect(url_for('dashboard', id_socio=dni))
        return render_template('login.html', error="Datos incorrectos")
    return render_template('login.html')

@app.route('/dashboard/<id_socio>')
def dashboard(id_socio):
    socio = Socio.query.get(id_socio)
    if not socio: return redirect(url_for('login'))
    
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    dia_hoy = dias[datetime.now().weekday()]
    
    # Elegimos la rutina según el día
    rutinas = {
        "Lunes": socio.rutina_lunes,
        "Martes": socio.rutina_martes,
        "Miércoles": socio.rutina_miercoles,
        "Jueves": socio.rutina_jueves,
        "Viernes": socio.rutina_viernes
    }
    rutina_hoy = rutinas.get(dia_hoy, "Día de descanso")
    
    return render_template('dashboard.html', socio=socio, rutina_hoy=rutina_hoy, dia=dia_hoy)

@app.route('/admin')
def admin_panel():
    socios = Socio.query.all()
    return render_template('admin.html', socios=socios)

@app.route('/admin/nuevo', methods=['GET', 'POST'])
def nuevo_socio():
    if request.method == 'POST':
        nuevo = Socio(
            dni=request.form.get('dni'),
            nombre=request.form.get('nombre').upper(),
            password=request.form.get('password'),
            plan=request.form.get('plan').upper(),
            vence=request.form.get('vence').upper()
        )
        db.session.add(nuevo)
        db.session.commit()
        return redirect(url_for('admin_panel'))
    return render_template('nuevo_socio.html')

@app.route('/admin/editar/<id_socio>', methods=['GET', 'POST'])
def editar_socio(id_socio):
    socio = Socio.query.get(id_socio)
    if request.method == 'POST':
        socio.nombre = request.form.get('nombre').upper()
        socio.plan = request.form.get('plan').upper()
        socio.vence = request.form.get('vence').upper()
        socio.rutina_lunes = request.form.get('rutina_lunes')
        socio.rutina_martes = request.form.get('rutina_martes')
        socio.rutina_miercoles = request.form.get('rutina_miercoles')
        socio.rutina_jueves = request.form.get('rutina_jueves')
        socio.rutina_viernes = request.form.get('rutina_viernes')
        db.session.commit()
        return redirect(url_for('admin_panel'))
    return render_template('editar_socio.html', socio=socio)

if __name__ == '__main__':
    app.run(debug=True)