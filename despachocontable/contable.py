from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

# --- FUNCIÓN PARA CREAR LA BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Tabla 1: Clientes del despacho
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS clientes_despacho (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rfc TEXT UNIQUE NOT NULL,
        razon_social TEXT NOT NULL,
        regimen_fiscal TEXT NOT NULL,
        correo TEXT
    );
    ''')
    
    # Tabla 2: Facturas y movimientos de cada cliente
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS movimientos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER NOT NULL,
        rfc_emisor TEXT NOT NULL,
        rfc_receptor TEXT NOT NULL,
        concepto TEXT NOT NULL,
        monto_subtotal REAL NOT NULL,
        iva REAL NOT NULL,
        monto_total REAL NOT NULL,
        tipo TEXT CHECK(tipo IN ('Ingreso', 'Gasto/Egreso')) NOT NULL,
        fecha DATE DEFAULT CURRENT_DATE,
        estado_sat TEXT DEFAULT 'Vigente',
        FOREIGN KEY(cliente_id) REFERENCES clientes_despacho(id)
    );
    ''')
    
    conn.commit()
    conn.close()

# Inicializar la base de datos al arrancar el programa
init_db()


# --- RUTAS DE LA APLICACIÓN ---

# Vista principal: Lista de Clientes del Despacho
@app.route('/')
def inicio():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clientes_despacho")
    clientes = cursor.fetchall()
    conn.close()
    return render_template('lista_clientes.html', clientes=clientes)

# Vista: Registrar nuevo cliente
@app.route('/nuevo_cliente', methods=['GET', 'POST'])
def nuevo_cliente():
    if request.method == 'POST':
        rfc = request.form['rfc']
        razon_social = request.form['razon_social']
        regimen = request.form['regimen']
        correo = request.form['correo']
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO clientes_despacho (rfc, razon_social, regimen_fiscal, correo) VALUES (?, ?, ?, ?)",
                       (rfc, razon_social, regimen, correo))
        conn.commit()
        conn.close()
        return redirect(url_for('inicio'))
        
    return render_template('nuevo_cliente.html')

# Vista: Dashboard de un cliente específico
@app.route('/cliente/<int:cliente_id>/dashboard')
def dashboard_cliente(cliente_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # 1. Obtener datos del cliente
    cursor.execute("SELECT * FROM clientes_despacho WHERE id = ?", (cliente_id,))
    cliente = cursor.fetchone()
    
    # 2. Obtener movimientos de este cliente
    cursor.execute("SELECT * FROM movimientos WHERE cliente_id = ? ORDER BY fecha DESC", (cliente_id,))
    movimientos = cursor.fetchall()
    
    # 3. Totales fiscales (Ingresos vs Gastos Deducibles)
    cursor.execute("SELECT SUM(monto_total) FROM movimientos WHERE cliente_id = ? AND tipo = 'Ingreso'", (cliente_id,))
    total_ingresos = cursor.fetchone()[0] or 0.0
    
    cursor.execute("SELECT SUM(monto_total) FROM movimientos WHERE cliente_id = ? AND tipo = 'Gasto/Egreso'", (cliente_id,))
    total_gastos = cursor.fetchone()[0] or 0.0
    
    # Balance gravable (Ingresos - Gastos)
    utilidad_o_perdida = total_ingresos + total_gastos
    
    conn.close()
    
    return render_template(
        'dashboard_despacho.html',
        cliente=cliente,
        movimientos=movimientos,
        ingresos=total_ingresos,
        gastos=total_gastos,
        utilidad=utilidad_o_perdida
    )

# Vista: Registrar nueva factura o movimiento para un cliente
@app.route('/cliente/<int:cliente_id>/nueva_factura', methods=['GET', 'POST'])
def nueva_factura(cliente_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    if request.method == 'POST':
        rfc_emisor = request.form['rfc_emisor']
        rfc_receptor = request.form['rfc_receptor']
        concepto = request.form['concepto']
        subtotal = float(request.form['subtotal'])
        iva = float(request.form['iva'])
        tipo = request.form['tipo']
        
        monto_total = subtotal + iva
        
        # Si es gasto/egreso, el total entra como número negativo para restar en el balance
        if tipo == 'Gasto/Egreso' and monto_total > 0:
            monto_total = -monto_total

        cursor.execute('''
            INSERT INTO movimientos 
            (cliente_id, rfc_emisor, rfc_receptor, concepto, monto_subtotal, iva, monto_total, tipo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (cliente_id, rfc_emisor, rfc_receptor, concepto, subtotal, iva, monto_total, tipo))
        
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard_cliente', cliente_id=cliente_id))
        
    cursor.execute("SELECT * FROM clientes_despacho WHERE id = ?", (cliente_id,))
    cliente = cliente = cursor.fetchone()
    conn.close()
    
    return render_template('nueva_factura.html', cliente=cliente)


# --- EJECUCIÓN DEL SERVIDOR ---
if __name__ == '__main__':
    app.run(debug=True)