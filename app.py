from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Base de datos simulada de Templo Fitness
SOCIOS = {
    "1234": {
        "nombre": "SANTINO", 
        "plan": "ANUAL", 
        "vence": "15 DIC 2026", 
        "rutina": [
            {"ej": "Sentadilla con Barra", "sets": "4x8"},
            {"ej": "Press de Banca Plano", "sets": "3x10"},
            {"ej": "Peso Muerto Rumano", "sets": "3x12"}
        ]
    },
    "4321": {
        "nombre": "BAUTISTA", 
        "plan": "MENSUAL", 
        "vence": "01 MAY 2026", 
        "rutina": [
            {"ej": "Prensa 45°", "sets": "4x15"},
            {"ej": "Sillón de Cuádriceps", "sets": "3x12"},
            {"ej": "Camilla de Isquios", "sets": "3x12"}
        ]
    }
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        dni = request.form.get('dni')
        
        # 1. Chequeamos si es el Admin
        if dni == "0000":
            return redirect(url_for('admin_panel'))
            
        # 2. Chequeamos si es un Socio
        if dni in SOCIOS:
            return redirect(url_for('dashboard', id_socio=dni))
            
        # 3. Si no es ninguno, error
        return render_template('login.html', error="DNI no encontrado")
    
    return render_template('login.html')

@app.route('/dashboard/<id_socio>')
def dashboard(id_socio):
    socio = SOCIOS.get(id_socio)
    if not socio:
        return redirect(url_for('login'))
    return render_template('dashboard.html', socio=socio)

@app.route('/admin')
def admin_panel():
    # Esta ruta muestra la lista de todos los socios
    return render_template('admin.html', socios=SOCIOS)

# IMPORTANTE: El run siempre debe ir al final de todo el archivo
if __name__ == '__main__':
    app.run(debug=True)