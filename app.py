from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime # Importante para los días

app = Flask(__name__)

# Modificamos la estructura para que soporte días
SOCIOS = {
    "1234": {
        "nombre": "SANTINO",
        "password": "123",
        "plan": "ANUAL",
        "vence": "15 DIC 2026",
        "rutina": {
            "Lunes": [{"ej": "Sentadilla", "sets": "4x8"}, {"ej": "Prensa", "sets": "3x12"}],
            "Miércoles": [{"ej": "Banca", "sets": "3x10"}, {"ej": "Cruces", "sets": "3x15"}],
            "Viernes": [{"ej": "Peso Muerto", "sets": "4x8"}]
        }
    }
}

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        dni = request.form.get('dni')
        password = request.form.get('password') # <--- Captura la clave del HTML
        
        if dni == "0000": 
            return redirect(url_for('admin_panel'))
            
        if dni in SOCIOS:
            # Compara la clave ingresada con la que está en el diccionario
            if SOCIOS[dni].get('password') == password:
                return redirect(url_for('dashboard', id_socio=dni))
            else:
                return render_template('login.html', error="Contraseña incorrecta")
                
        return render_template('login.html', error="DNI no encontrado")
    return render_template('login.html')

@app.route('/dashboard/<id_socio>')
def dashboard(id_socio):
    socio = SOCIOS.get(id_socio)
    if not socio: return redirect(url_for('login'))
    
    # LÓGICA DEL DÍA
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    dia_actual = dias_semana[datetime.now().weekday()] # Detecta el día real
    
    # Obtenemos la rutina de hoy o mandamos una lista vacía si no entrena hoy
    rutina_hoy = socio['rutina'].get(dia_actual, [])
    
    return render_template('dashboard.html', socio=socio, rutina_hoy=rutina_hoy, dia=dia_actual)