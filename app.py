from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from dateutil.relativedelta import relativedelta

app = Flask(__name__)

# --- LÓGICA DE FECHAS ---
def restan_dias(fecha_str):
    try:
        vence_dt = datetime.strptime(fecha_str, '%d/%m/%Y')
        hoy = datetime.now()
        delta = vence_dt - hoy
        return delta.days + 1
    except:
        return 0

@app.context_processor
def utility_processor():
    return dict(restan_dias=restan_dias)

# --- CONFIGURACIÓN DE BASE DE DATOS (SUPABASE) ---
# Usamos el puerto 6543 que es más estable para Vercel
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+pg8000://postgres:312111Santi%40@db.outmumjurvsesziislzu.supabase.co:5432/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Esto es para que pg8000 no se queje del SSL
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "connect_args": {
        "ssl": True
    }
}


# --- MODELO DE LA BASE DE DATOS ---
class Socio(db.Model):
    dni = db.Column(db.String(20), primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    plan = db.Column(db.String(50))
    vence = db.Column(db.String(50))
    rutina_lunes = db.Column(db.Text, default="")
    rutina_martes = db.Column(db.Text, default="")
    rutina_miercoles = db.Column(db.Text, default="")
    rutina_jueves = db.Column(db.Text, default="")
    rutina_viernes = db.Column(db.Text, default="")

# --- CREAR TABLAS ---
#with app.app_context():
 #   db.create_all()

# --- RUTAS ---
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
    
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    dia_hoy_nombre = dias_semana[datetime.now().weekday()]
    
    dias_restantes = restan_dias(socio.vence)
    
    rutinas = {
        "Lunes": socio.rutina_lunes, "Martes": socio.rutina_martes,
        "Miércoles": socio.rutina_miercoles, "Jueves": socio.rutina_jueves,
        "Viernes": socio.rutina_viernes
    }
    rutina_hoy = rutinas.get(dia_hoy_nombre, "Día de descanso")
    
    return render_template('dashboard.html', 
                           socio=socio, 
                           rutina_hoy=rutina_hoy, 
                           dia=dia_hoy_nombre, 
                           restan=dias_restantes)

@app.route('/admin')
def admin_panel():
    socios = Socio.query.all()
    return render_template('admin.html', socios=socios)

@app.route('/admin/nuevo', methods=['GET', 'POST'])
def nuevo_socio():
    if request.method == 'POST':
        plan = request.form.get('plan')
        hoy = datetime.now()
        
        duracion = {
            "MENSUAL": relativedelta(months=1),
            "TRIMESTRAL": relativedelta(months=3),
            "SEMESTRAL": relativedelta(months=6),
            "ANUAL": relativedelta(years=1)
        }
        
        vencimiento = hoy + duracion.get(plan, relativedelta(months=1))
            
        nuevo = Socio(
            dni=request.form.get('dni'),
            nombre=request.form.get('nombre').upper(),
            password=request.form.get('password'),
            plan=plan,
            vence=vencimiento.strftime('%d/%m/%Y')
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