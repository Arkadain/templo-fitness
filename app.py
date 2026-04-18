from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import os
from dateutil.relativedelta import relativedelta
from sqlalchemy.exc import IntegrityError
from supabase import create_client, Client

SUPABASE_URL = "https://outmumjurvsesziislzu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im91dG11bWp1cnZzZXN6aWlzbHp1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU4MzA0OTMsImV4cCI6MjA5MTQwNjQ5M30.fK3lLTSINKR4zBJQOotM0N2zUL-MJtny169wI-vLO24"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)

# --- SECRET KEY ---
app.secret_key = os.environ.get('SECRET_KEY', "TemploBaraderoSeguro2026!")

# --- PROTECCIÓN CSRF ---
csrf = CSRFProtect(app)

# --- CONFIGURACIÓN DE BASE DE DATOS ---
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'postgresql://postgres.outmumjurvsesziislzu:312111Santi%40@aws-1-us-east-2.pooler.supabase.com:5432/postgres'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "connect_args": {
        "sslmode": "require"
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
    genero = db.Column(db.String(20), default="MASCULINO") # NUEVO CAMPO
    rutina_lunes = db.Column(db.Text, default="")
    rutina_martes = db.Column(db.Text, default="")
    rutina_miercoles = db.Column(db.Text, default="")
    rutina_jueves = db.Column(db.Text, default="")
    rutina_viernes = db.Column(db.Text, default="")
    rutina_sabado = db.Column(db.Text, default="")
    foto = db.Column(db.String(500), default='')

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

# --- SUBIR FOTO DE PERFIL ---
@app.route('/subir_foto/<id_socio>', methods=['POST'])
def subir_foto(id_socio):
    # Chequeo de seguridad
    if session.get('user_id') != id_socio and not session.get('admin'):
        return redirect(url_for('login'))

    if 'foto' not in request.files:
        return redirect(url_for('perfil', id_socio=id_socio))

    file = request.files['foto']
    if file.filename == '':
        return redirect(url_for('perfil', id_socio=id_socio))

    if file:
        try:
            # Leemos la foto
            file_bytes = file.read()
            # Sacamos la extensión (ej: jpg, png)
            file_ext = file.filename.rsplit('.', 1)[1].lower()
            # Bautizamos la foto (ej: avatar_34556122.jpg)
            filename = f"avatar_{id_socio}.{file_ext}"

            # Subimos a Supabase (upsert=True hace que sobreescriba la vieja si cambia la foto)
            supabase.storage.from_('avatars').upload(
                path=filename,
                file=file_bytes,
                file_options={"content-type": file.content_type, "upsert": "true"}
            )

            # Pedimos el link público
            public_url = supabase.storage.from_('avatars').get_public_url(filename)

            # Guardamos el link en la base de datos
            socio = Socio.query.get(id_socio)
            socio.foto = public_url
            db.session.commit()

        except Exception as e:
            print("Error al subir foto:", e)

    return redirect(url_for('perfil', id_socio=id_socio))

# --- RUTAS PÚBLICAS ---
@app.route('/')
def index():
    return render_template('index.html')

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

        return render_template('login.html', error="Datos incorrectos")

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard/<id_socio>')
def dashboard(id_socio):
    if session.get('user_id') != id_socio and not session.get('admin'):
        return redirect(url_for('login'))

    socio = Socio.query.get(id_socio)
    if not socio:
        return redirect(url_for('login'))

    hoy = fecha_hoy_argentina()
    
    # Acá ya traés todas las asistencias del socio
    asistencias = Asistencia.query.filter_by(dni_socio=id_socio).all()
    
    # MAGIA: Contamos cuántas hay en esa lista para las sesiones totales
    total_entrenamientos = len(asistencias)
    
    semanas_asistidas = set()
    for a in asistencias:
        año, semana, _ = a.fecha.isocalendar()
        semanas_asistidas.add((año, semana))
        
    sorted_weeks = sorted(list(semanas_asistidas), reverse=True)
    racha = 0
    
    if sorted_weeks:
        curr_year, curr_week, _ = hoy.isocalendar()
        last_week_date = hoy - relativedelta(days=7)
        last_year, last_week, _ = last_week_date.isocalendar()
        latest_year, latest_week = sorted_weeks[0]
        
        if (latest_year, latest_week) == (curr_year, curr_week) or (latest_year, latest_week) == (last_year, last_week):
            expected_y, expected_w = latest_year, latest_week
            for y, w in sorted_weeks:
                if (y, w) == (expected_y, expected_w):
                    racha += 1
                    prev_date = date.fromisocalendar(y, w, 1) - relativedelta(days=7)
                    expected_y, expected_w, _ = prev_date.isocalendar()
                else:
                    break

    # Le pasamos la nueva variable total_entrenamientos al final del render_template
    return render_template('dashboard.html', socio=socio, racha=racha, semanas_asistidas=semanas_asistidas, total_entrenamientos=total_entrenamientos)

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
    return render_template('rutina.html', socio=socio, rutina_hoy=rutina_hoy, dia=dia_hoy_nombre)

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

    return render_template('fuerza.html', socio=socio, registros=registros, prs=prs)

@app.route('/perfil/<id_socio>')
def perfil(id_socio):
    if session.get('user_id') != id_socio and not session.get('admin'):
        return redirect(url_for('login'))
        
    socio = Socio.query.get(id_socio)
    
    # --- CALCULAR RACHA Y TOTAL PARA EL PERFIL ---
    hoy = fecha_hoy_argentina()
    asistencias = Asistencia.query.filter_by(dni_socio=id_socio).all()
    
    # Total de días que vino en su historia
    total_entrenamientos = len(asistencias)
    
    # Calcular Racha Semanal
    semanas_asistidas = set()
    for a in asistencias:
        año, semana, _ = a.fecha.isocalendar()
        semanas_asistidas.add((año, semana))
        
    sorted_weeks = sorted(list(semanas_asistidas), reverse=True)
    racha = 0
    
    if sorted_weeks:
        curr_year, curr_week, _ = hoy.isocalendar()
        last_week_date = hoy - relativedelta(days=7)
        last_year, last_week, _ = last_week_date.isocalendar()
        
        latest_year, latest_week = sorted_weeks[0]
        
        if (latest_year, latest_week) == (curr_year, curr_week) or (latest_year, latest_week) == (last_year, last_week):
            expected_y, expected_w = latest_year, latest_week
            for y, w in sorted_weeks:
                if (y, w) == (expected_y, expected_w):
                    racha += 1
                    prev_date = date.fromisocalendar(y, w, 1) - relativedelta(days=7)
                    expected_y, expected_w, _ = prev_date.isocalendar()
                else:
                    break

    return render_template('perfil.html', socio=socio, restan=restan_dias(socio.vence), racha=racha, total_entrenamientos=total_entrenamientos)

# --- NUEVA RUTA: SALÓN DE LA FAMA (RANKING) ---
@app.route('/ranking')
def ranking():
    if not session.get('user_id') and not session.get('admin'):
        return redirect(url_for('login'))
        
    ejercicios = ["Sentadilla Libre", "Press de Banca Plano", "Peso Muerto"]
    tops = {'MASCULINO': {}, 'FEMENINO': {}}
    
    for genero in ['MASCULINO', 'FEMENINO']:
        for ej in ejercicios:
            registros = db.session.query(
                Socio.dni,
                Socio.nombre,
                db.func.max(RegistroPesos.peso).label('max_peso')
            ).join(RegistroPesos, Socio.dni == RegistroPesos.dni_socio)\
             .filter(RegistroPesos.ejercicio == ej, Socio.genero == genero)\
             .group_by(Socio.dni, Socio.nombre)\
             .order_by(db.func.max(RegistroPesos.peso).desc())\
             .limit(10).all()
             
            tops[genero][ej] = [{'nombre': r.nombre, 'peso': float(r.max_peso), 'dni': r.dni} for r in registros]

    socio_actual = Socio.query.get(session.get('user_id'))
    return render_template('ranking.html', tops=tops, socio_actual=socio_actual)

# --- RUTAS DE ADMINISTRACIÓN ---
@app.route('/admin')
def admin_panel():
    if not session.get('admin'):
        return redirect(url_for('login'))
        
    socios = Socio.query.all()
    
    # Calcular cuántos socios dieron el presente hoy (A PRUEBA DE BALAS)
    hoy_dt = fecha_hoy_argentina()
    # Verificamos si tiene el atributo 'date' antes de usarlo
    hoy = hoy_dt.date() if hasattr(hoy_dt, 'date') else hoy_dt
    
    asistencias_todas = Asistencia.query.all()
    
    ingresos_hoy = 0
    for a in asistencias_todas:
        # Hacemos lo mismo con la fecha de asistencia
        a_fecha = a.fecha.date() if hasattr(a.fecha, 'date') else a.fecha
        if a_fecha == hoy:
            ingresos_hoy += 1
            
    return render_template('admin.html', socios=socios, ingresos_hoy=ingresos_hoy)

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
        genero = request.form.get('genero', 'MASCULINO') # NUEVO

        if not dni or not nombre or not password_raw or not plan:
            flash("Todos los campos son obligatorios.", "error")
            return render_template('nuevo_socio.html')

        if Socio.query.get(dni):
            flash(f"Ya existe un socio con el DNI {dni}.", "error")
            return render_template('nuevo_socio.html')

        duracion = {"MENSUAL": 1, "TRIMESTRAL": 3, "SEMESTRAL": 6, "ANUAL": 12}
        vencimiento = fecha_hoy_argentina() + relativedelta(months=duracion.get(plan.upper(), 1))

        nuevo = Socio(
            dni=dni, nombre=nombre.upper(), password=generate_password_hash(password_raw),
            plan=plan.upper(), genero=genero.upper(), vence=vencimiento.strftime('%d/%m/%Y')
        )
        db.session.add(nuevo)
        db.session.commit()
        flash(f'Socio {nuevo.nombre} agregado.', 'success')
        return redirect(url_for('admin_panel'))

    return render_template('nuevo_socio.html')

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
        socio.genero = request.form.get('genero', 'MASCULINO').upper() # NUEVO

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

    return render_template('editar_socio.html', socio=socio, vence_html=vence_html)

if __name__ == '__main__':
    app.run(debug=False)