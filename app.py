from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import os
from dateutil.relativedelta import relativedelta
from sqlalchemy.exc import IntegrityError

# Le decimos a Vercel EXACTAMENTE dónde buscar las plantillas
base_dir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, template_folder=os.path.join(base_dir, 'templates'))

# --- SECRET KEY (Fija para evitar errores CSRF en Vercel) ---
app.secret_key = "TemploBaraderoSeguro2026!"

# --- PROTECCIÓN CSRF ---
csrf = CSRFProtect(app)

# --- CONFIGURACIÓN DE BASE DE DATOS ---
_raw_db_url = os.environ.get(
    'DATABASE_URL',
    'postgresql://postgres.outmumjurvsesziislzu:312111Santi%40@aws-1-us-east-2.pooler.supabase.com:5432/postgres'
)
# Vercel requiere pg8000 (driver Python puro). Ajustamos el prefijo si hace falta.
if _raw_db_url.startswith('postgresql://') or _raw_db_url.startswith('postgres://'):
    _raw_db_url = _raw_db_url.replace('postgresql://', 'postgresql+pg8000://', 1).replace('postgres://', 'postgresql+pg8000://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = _raw_db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "connect_args": {
        "ssl_context": True
    }
}
db = SQLAlchemy(app)

# --- LÓGICA DE FECHAS (Escudo Horario Argentina UTC-3) ---
def fecha_hoy_argentina():
    return (datetime.utcnow() - relativedelta(hours=3)).date()

def restan_dias(fecha_str):
    if not fecha_str:
        return 0
    try:
        vence_dt = datetime.strptime(fecha_str, '%d/%m/%Y').date()
        hoy = fecha_hoy_argentina()
        delta = vence_dt - hoy
        return delta.days
    except Exception as e:
        print(f"Error en fecha: {e}")
        return 0

@app.context_processor
def utility_processor():
    return dict(restan_dias=restan_dias)

# --- MODELOS DE LA BASE DE DATOS ---
class Socio(db.Model):
    __tablename__ = 'socio'
    dni = db.Column(db.String(20), primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(256), nullable=False)
    plan = db.Column(db.String(50))
    vence = db.Column(db.String(50))
    rutina_lunes = db.Column(db.Text, default="")
    rutina_martes = db.Column(db.Text, default="")
    rutina_miercoles = db.Column(db.Text, default="")
    rutina_jueves = db.Column(db.Text, default="")
    rutina_viernes = db.Column(db.Text, default="")
    rutina_sabado = db.Column(db.Text, default="")

class Asistencia(db.Model):
    __tablename__ = 'asistencia'
    id = db.Column(db.Integer, primary_key=True)
    dni_socio = db.Column(db.String(20), db.ForeignKey('socio.dni', ondelete='CASCADE'), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    __table_args__ = (db.UniqueConstraint('dni_socio', 'fecha', name='uq_asistencia_diaria'),)

class RegistroPesos(db.Model):
    __tablename__ = 'registro_pesos'
    id = db.Column(db.Integer, primary_key=True)
    dni_socio = db.Column(db.String(20), db.ForeignKey('socio.dni', ondelete='CASCADE'), nullable=False)
    ejercicio = db.Column(db.String(100), nullable=False)
    peso = db.Column(db.Numeric(5, 2), nullable=False)
    repeticiones = db.Column(db.Integer, nullable=False)
    fecha = db.Column(db.Date, nullable=False)

# --- RUTAS PÚBLICAS ---
@app.route('/')
def index():
    return render_template('public/index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        dni = request.form.get('dni', '').strip()
        password = request.form.get('password', '')

        ADMIN_USER = os.environ.get('ADMIN_USER', '0000')
        ADMIN_PASS = os.environ.get('ADMIN_PASS', 'admin123')

        if dni == ADMIN_USER and password == ADMIN_PASS:
            session.clear()
            session['admin'] = True
            return redirect(url_for('admin_panel'))

        socio = Socio.query.get(dni)

        password_ok = False
        if socio:
            if socio.password.startswith('pbkdf2:') or socio.password.startswith('scrypt:'):
                password_ok = check_password_hash(socio.password, password)
            else:
                if socio.password == password:
                    password_ok = True
                    socio.password = generate_password_hash(password)
                    db.session.commit()

        if password_ok:
            session.clear()
            session['user_id'] = dni
            return redirect(url_for('dashboard', id_socio=dni))

        return render_template('public/login.html', error="Datos incorrectos")

    return render_template('public/login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- RUTAS DEL ALUMNO ---

@app.route('/dashboard/<id_socio>')
def dashboard(id_socio):
    if session.get('user_id') != id_socio and not session.get('admin'):
        return redirect(url_for('login'))

    socio = Socio.query.get(id_socio)
    if not socio:
        return redirect(url_for('login'))

    hoy = fecha_hoy_argentina()
    
    asistencias = Asistencia.query.filter_by(dni_socio=id_socio).all()
    fechas_asistidas = [a.fecha for a in asistencias]
    
    racha = 0
    fecha_check = hoy
    if fecha_check not in fechas_asistidas:
        fecha_check -= relativedelta(days=1)
        
    while fecha_check in fechas_asistidas:
        racha += 1
        fecha_check -= relativedelta(days=1)
        
    dias_semana_corto = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sa", "Do"]
    ultimos_7_dias = [hoy - relativedelta(days=i) for i in range(6, -1, -1)]
    
    historial_strava = []
    for d in ultimos_7_dias:
        historial_strava.append({
            'nombre': dias_semana_corto[d.weekday()],
            'asistio': d in fechas_asistidas,
            'es_hoy': d == hoy
        })

    return render_template('socio/dashboard.html', socio=socio, racha=racha, historial_strava=historial_strava)

@app.route('/asistencia/presente', methods=['POST'])
def dar_presente():
    dni = session.get('user_id')
    if not dni:
        return redirect(url_for('login'))
        
    try:
        nueva_asistencia = Asistencia(dni_socio=dni, fecha=fecha_hoy_argentina())
        db.session.add(nueva_asistencia)
        db.session.commit()
        flash("¡Entrenamiento registrado! Que sea un gran día.", "success")
    except IntegrityError:
        db.session.rollback()
        flash("Ya te diste el presente hoy. ¡A entrenar duro!", "error")
        
    return redirect(url_for('dashboard', id_socio=dni))

@app.route('/rutina/<id_socio>')
def rutina(id_socio):
    if session.get('user_id') != id_socio and not session.get('admin'):
        return redirect(url_for('login'))
        
    socio = Socio.query.get(id_socio)
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    dia_hoy_nombre = dias_semana[fecha_hoy_argentina().weekday()]

    rutinas = {
        "Lunes": socio.rutina_lunes, "Martes": socio.rutina_martes,
        "Miércoles": socio.rutina_miercoles, "Jueves": socio.rutina_jueves,
        "Viernes": socio.rutina_viernes, "Sábado": socio.rutina_sabado
    }
    rutina_hoy = rutinas.get(dia_hoy_nombre, "")
    
    return render_template('socio/rutina.html', socio=socio, rutina_hoy=rutina_hoy, dia=dia_hoy_nombre)

@app.route('/fuerza/<id_socio>', methods=['GET', 'POST'])
def fuerza(id_socio):
    if session.get('user_id') != id_socio and not session.get('admin'):
        return redirect(url_for('login'))
        
    socio = Socio.query.get(id_socio)

    if request.method == 'POST':
        ejercicio = request.form.get('ejercicio')
        peso = request.form.get('peso')
        repeticiones = request.form.get('repeticiones')
        
        nuevo_registro = RegistroPesos(
            dni_socio=id_socio, ejercicio=ejercicio, peso=peso,
            repeticiones=repeticiones, fecha=fecha_hoy_argentina()
        )
        db.session.add(nuevo_registro)
        db.session.commit()
        flash("¡Registro guardado con éxito!", "success")
        return redirect(url_for('fuerza', id_socio=id_socio))

    registros = RegistroPesos.query.filter_by(dni_socio=id_socio).order_by(RegistroPesos.fecha.desc(), RegistroPesos.id.desc()).all()
    prs = db.session.query(RegistroPesos.ejercicio, db.func.max(RegistroPesos.peso).label('max_peso')).filter_by(dni_socio=id_socio).group_by(RegistroPesos.ejercicio).all()

    return render_template('socio/fuerza.html', socio=socio, registros=registros, prs=prs)

@app.route('/perfil/<id_socio>')
def perfil(id_socio):
    if session.get('user_id') != id_socio and not session.get('admin'):
        return redirect(url_for('login'))
    socio = Socio.query.get(id_socio)
    return render_template('socio/perfil.html', socio=socio, restan=restan_dias(socio.vence))


# --- RUTAS DE ADMINISTRACIÓN ---
@app.route('/admin')
def admin_panel():
    if not session.get('admin'):
        return redirect(url_for('login'))
    socios = Socio.query.all()
    return render_template('admin/admin.html', socios=socios)

@app.route('/eliminar/<dni>', methods=['POST'])
def eliminar_socio(dni):
    if not session.get('admin'):
        return redirect(url_for('login'))
    socio_a_borrar = Socio.query.get(dni)
    if socio_a_borrar:
        db.session.delete(socio_a_borrar)
        db.session.commit()
        flash(f'Socio eliminado correctamente.', 'success')
    return redirect('/admin')

@app.route('/admin/nuevo', methods=['GET', 'POST'])
def nuevo_socio():
    if not session.get('admin'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        dni = request.form.get('dni', '').strip()
        nombre = request.form.get('nombre', '').strip()
        password_raw = request.form.get('password', '')
        plan = request.form.get('plan', '')

        if not dni or not nombre or not password_raw or not plan:
            flash("Todos los campos son obligatorios.", "error")
            return render_template('admin/nuevo_socio.html')

        if Socio.query.get(dni):
            flash(f"Ya existe un socio con el DNI {dni}.", "error")
            return render_template('admin/nuevo_socio.html')

        duracion = {"MENSUAL": 1, "TRIMESTRAL": 3, "SEMESTRAL": 6, "ANUAL": 12}
        vencimiento = fecha_hoy_argentina() + relativedelta(months=duracion.get(plan.upper(), 1))

        nuevo = Socio(
            dni=dni, nombre=nombre.upper(), password=generate_password_hash(password_raw),
            plan=plan.upper(), vence=vencimiento.strftime('%d/%m/%Y')
        )
        db.session.add(nuevo)
        db.session.commit()
        flash(f'Socio {nuevo.nombre} agregado.', 'success')
        return redirect(url_for('admin_panel'))

    return render_template('admin/nuevo_socio.html')

@app.route('/admin/renovar/<id_socio>', methods=['POST'])
def renovar_socio(id_socio):
    if not session.get('admin'):
        return redirect(url_for('login'))

    socio = Socio.query.get(id_socio)
    if socio:
        nuevo_plan = request.form.get('plan', '').upper()
        fecha_pago_str = request.form.get('fecha_pago', '')
        try:
            fecha_pago = datetime.strptime(fecha_pago_str, '%Y-%m-%d').date()
            duracion = {"MENSUAL": 1, "TRIMESTRAL": 3, "SEMESTRAL": 6, "ANUAL": 12}
            nuevo_vencimiento = fecha_pago + relativedelta(months=duracion.get(nuevo_plan, 1))
            socio.plan = nuevo_plan
            socio.vence = nuevo_vencimiento.strftime('%d/%m/%Y')
            db.session.commit()
            flash(f"Membresía renovada.", "success")
        except Exception as e:
            flash("Error en la fecha.", "error")

    return redirect(url_for('admin_panel'))

@app.route('/admin/editar/<id_socio>', methods=['GET', 'POST'])
def editar_socio(id_socio):
    if not session.get('admin'):
        return redirect(url_for('login'))

    socio = Socio.query.get(id_socio)
    if not socio:
        flash("Socio no encontrado.", "error")
        return redirect(url_for('admin_panel'))

    if request.method == 'POST':
        socio.nombre = request.form.get('nombre', '').upper()
        socio.plan = request.form.get('plan', '').upper()

        nueva_password = request.form.get('password', '').strip()
        if nueva_password:
            socio.password = generate_password_hash(nueva_password)

        fecha_html = request.form.get('vence', '')
        if fecha_html and "-" in fecha_html:
            try:
                fecha_obj = datetime.strptime(fecha_html, '%Y-%m-%d')
                socio.vence = fecha_obj.strftime('%d/%m/%Y')
            except:
                socio.vence = fecha_html
        else:
            socio.vence = fecha_html

        socio.rutina_lunes = request.form.get('rutina_lunes', '')
        socio.rutina_martes = request.form.get('rutina_martes', '')
        socio.rutina_miercoles = request.form.get('rutina_miercoles', '')
        socio.rutina_jueves = request.form.get('rutina_jueves', '')
        socio.rutina_viernes = request.form.get('rutina_viernes', '')
        socio.rutina_sabado = request.form.get('rutina_sabado', '')

        db.session.commit()
        flash("Datos actualizados.", "success")
        return redirect(url_for('admin_panel'))

    vence_html = ""
    if socio.vence:
        try:
            vence_html = datetime.strptime(socio.vence, '%d/%m/%Y').strftime('%Y-%m-%d')
        except:
            pass

    return render_template('admin/editar_socio.html', socio=socio, vence_html=vence_html)

if __name__ == '__main__':
    app.run(debug=False)