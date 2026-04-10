from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Base de datos simulada
SOCIOS = {
    "1234": {
        "nombre": "SANTINO", 
        "plan": "ANUAL", 
        "vence": "15 DIC 2026", 
        "rutina": [
            {"ej": "Sentadilla con Barra", "sets": "4x8"},
            {"ej": "Press de Banca Plano", "sets": "3x10"}
        ]
    },
    "4321": {
        "nombre": "BAUTISTA", 
        "plan": "MENSUAL", 
        "vence": "01 MAY 2026", 
        "rutina": [
            {"ej": "Prensa 45°", "sets": "4x15"}
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
        if dni == "0000":
            return redirect(url_for('admin_panel'))
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

@app.route('/admin/nuevo', methods=['GET', 'POST'])
def nuevo_socio():
    if request.method == 'POST':
        dni = request.form.get('dni')
        SOCIOS[dni] = {
            "nombre": request.form.get('nombre').upper(),
            "plan": request.form.get('plan').upper(),
            "vence": request.form.get('vence').upper(),
            "rutina": []
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

# IMPORTANTE: Esto siempre al final
if __name__ == '__main__':
    app.run(debug=True)