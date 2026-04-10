from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime

app = Flask(__name__)

# Base de datos simulada con soporte para Días y Contraseñas
SOCIOS = {
    "1234": {
        "nombre": "SANTINO", 
        "password": "123",
        "plan": "ANUAL", 
        "vence": "15 DIC 2026", 
        "rutina": {
            "Lunes": [{"ej": "Pecho Plano", "sets": "4x10"}, {"ej": "Inclinado", "sets": "3x12"}],
            "Martes": [{"ej": "Sentadilla", "sets": "4x8"}],
            "Miércoles": [{"ej": "Press Militar", "sets": "4x10"}],
            "Jueves": [{"ej": "Peso Muerto", "sets": "3x8"}],
            "Viernes": [{"ej": "Biceps/Triceps", "sets": "4x12"}],
            "Sábado": [],
            "Domingo": []
        }
    },
    "4321": {
        "nombre": "BAUTISTA", 
        "password": "456",
        "plan": "MENSUAL", 
        "vence": "01 MAY 2026", 
        "rutina": {
            "Lunes": [{"ej": "Prensa 45°", "sets": "4x15"}],
            "Viernes": [{"ej": "Camilla Isquios", "sets": "3x12"}]
        }
    }
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        dni = request.form.get('dni')
        password = request.form.get('password')
        
        if dni == "0000":
            return redirect(url_for('admin_panel'))
            
        if dni in SOCIOS:
            if SOCIOS[dni].get('password') == password:
                return redirect(url_for('dashboard', id_socio=dni))
            return render_template('login.html', error="Contraseña incorrecta")
            
        return render_template('login.html', error="DNI no encontrado")
    return render_template('login.html')

@app.route('/dashboard/<id_socio>')
def dashboard(id_socio):
    socio = SOCIOS.get(id_socio)
    if not socio:
        return redirect(url_for('login'))
    
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    dia_hoy = dias[datetime.now().weekday()]
    
    # Obtenemos la rutina del día actual del diccionario
    rutina_hoy = socio.get('rutina', {}).get(dia_hoy, [])
    
    return render_template('dashboard.html', socio=socio, rutina_hoy=rutina_hoy, dia=dia_hoy)

@app.route('/admin')
def admin_panel():
    return render_template('admin.html', socios=SOCIOS)

@app.route('/admin/nuevo', methods=['GET', 'POST'])
def nuevo_socio():
    if request.method == 'POST':
        dni = request.form.get('dni')
        SOCIOS[dni] = {
            "nombre": request.form.get('nombre').upper(),
            "password": request.form.get('password'),
            "plan": request.form.get('plan').upper(),
            "vence": request.form.get('vence').upper(),
            "rutina": {}
        }
        return redirect(url_for('admin_panel'))
    return render_template('nuevo_socio.html')

@app.route('/admin/editar/<id_socio>', methods=['GET', 'POST'])
def editar_socio(id_socio):
    socio = SOCIOS.get(id_socio)
    if not socio: return "No encontrado", 404
    if request.method == 'POST':
        socio['nombre'] = request.form.get('nombre').upper()
        socio['plan'] = request.form.get('plan').upper()
        socio['vence'] = request.form.get('vence').upper()
        return redirect(url_for('admin_panel'))
    return render_template('editar_socio.html', socio=socio, id=id_socio)

if __name__ == '__main__':
    app.run(debug=True)