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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        dni = request.form.get('dni')
        
        # EL ADMIN VA PRIMERO (fuera del diccionario)
        if dni == "0000":
            return redirect(url_for('admin_panel'))
            
        # DESPUÉS BUSCAMOS SOCIOS
        if dni in SOCIOS:
            return redirect(url_for('dashboard', id_socio=dni))
            
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
    return render_template('admin.html', socios=SOCIOS)

# --- NUEVA RUTA: ALTA DE SOCIO ---
@app.route('/admin/nuevo', methods=['GET', 'POST'])
def nuevo_socio():
    if request.method == 'POST':
        dni = request.form.get('dni')
        nombre = request.form.get('nombre').upper()
        plan = request.form.get('plan').upper()
        vence = request.form.get('vence').upper()
        
        SOCIOS[dni] = {
            "nombre": nombre,
            "plan": plan,
            "vence": vence,
            "rutina": [] # Se crea vacío para asignarle ejercicios después
        }
        return redirect(url_for('admin_panel'))
    return render_template('nuevo_socio.html')

# --- RUTA: EDITAR SOCIO ---
@app.route('/admin/editar/<id_socio>', methods=['GET', 'POST'])
def editar_socio(id_socio):
    socio = SOCIOS.get(id_socio)
    if not socio:
        return "Socio no encontrado", 404
    if request.method == 'POST':
        socio['nombre'] = request.form.get('nombre').upper()
        socio['plan'] = request.form.get('plan').upper()
        socio['vence'] = request.form.get('vence').upper()
        return redirect(url_for('admin_panel'))
    return render_template('editar_socio.html', socio=socio, id=id_socio)

# EL "RUN" SIEMPRE AL FINAL
if __name__ == '__main__':
    app.run(debug=True)