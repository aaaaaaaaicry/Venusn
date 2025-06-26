from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime
import threading

app = Flask(__name__, static_folder='frontend', static_url_path='')
CORS(app)

# Dados simples na memória
products = []
orders = []
order_id_counter = 1
lock = threading.Lock()

# Senhas fixas
CLIENT_PASS = 'venusmn137'
ADMIN_PASS = 'admvenus1377'

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

# API produtos
@app.route('/api/products', methods=['GET'])
def get_products():
    return jsonify(products)

# Login
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    senha = data.get('senha','')
    if senha == ADMIN_PASS:
        return jsonify({'role': 'admin'})
    elif senha == CLIENT_PASS:
        return jsonify({'role': 'user'})
    else:
        return jsonify({'error': 'Senha incorreta'}), 401

# Criar/editar produtos (admin)
@app.route('/api/admin/products', methods=['POST'])
def add_product():
    token = request.headers.get('X-Admin-Token', '')
    if token != ADMIN_PASS:
        return jsonify({'error':'Não autorizado'}), 403

    data = request.json
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    price = data.get('price', 0)
    images = data.get('images', [])
    stock = data.get('stock', 0)

    if not name or price <= 0 or stock < 0:
        return jsonify({'error':'Dados inválidos'}), 400

    global order_id_counter
    with lock:
        new_id = max([p['id'] for p in products], default=0) + 1
        product = {
            'id': new_id,
            'name': name,
            'description': description,
            'price': price,
            'images': images,
            'stock': stock
        }
        products.append(product)

    return jsonify({'success': True})

@app.route('/api/admin/products/<int:prod_id>', methods=['PUT'])
def edit_product(prod_id):
    token = request.headers.get('X-Admin-Token', '')
    if token != ADMIN_PASS:
        return jsonify({'error':'Não autorizado'}), 403

    data = request.json
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    price = data.get('price', 0)
    images = data.get('images', [])
    stock = data.get('stock', 0)

    if not name or price <= 0 or stock < 0:
        return jsonify({'error':'Dados inválidos'}), 400

    with lock:
        for p in products:
            if p['id'] == prod_id:
                p['name'] = name
                p['description'] = description
                p['price'] = price
                p['images'] = images
                p['stock'] = stock
                return jsonify({'success': True})
    return jsonify({'error': 'Produto não encontrado'}), 404

@app.route('/api/admin/products/<int:prod_id>', methods=['DELETE'])
def delete_product(prod_id):
    token = request.headers.get('X-Admin-Token', '')
    if token != ADMIN_PASS:
        return jsonify({'error':'Não autorizado'}), 403
    with lock:
        for i,p in enumerate(products):
            if p['id'] == prod_id:
                products.pop(i)
                return jsonify({'success': True})
    return jsonify({'error': 'Produto não encontrado'}), 404

# Criar pedido
@app.route('/api/orders', methods=['POST'])
def create_order():
    global order_id_counter
    data = request.json
    senha = data.get('senha', '')
    if senha not in [CLIENT_PASS, ADMIN_PASS]:
        return jsonify({'error':'Não autorizado'}), 403

    product_id = data.get('product_id')
    user_id = data.get('user_id','').strip()
    if not user_id or not product_id:
        return jsonify({'error':'Dados inválidos'}), 400

    with lock:
        prod = next((p for p in products if p['id'] == product_id), None)
        if not prod:
            return jsonify({'error':'Produto não encontrado'}), 404
        if prod['stock'] <= 0:
            return jsonify({'error':'Produto sem estoque'}), 400

        order = {
            'order_id': order_id_counter,
            'product_id': prod['id'],
            'product_name': prod['name'],
            'product_price': prod['price'],
            'user_id': user_id,
            'date': datetime.now().isoformat(),
            'status': 'pendente'
        }
        orders.append(order)
        order_id_counter += 1
    return jsonify({'success': True})

# Listar pedidos pendentes para admin
@app.route('/api/admin/orders', methods=['GET'])
def admin_orders():
    token = request.headers.get('X-Admin-Token', '')
    if token != ADMIN_PASS:
        return jsonify({'error':'Não autorizado'}), 403
    with lock:
        pendentes = [o for o in orders if o['status']=='pendente']
        # Adicionar estoque atual do produto na resposta
        for o in pendentes:
            p = next((p for p in products if p['id']==o['product_id']), None)
            o['product_stock'] = p['stock'] if p else 0
        return jsonify(pendentes)

# Atualizar status pedido admin (aprovar ou reprovar)
@app.route('/api/admin/orders/<int:order_id>', methods=['PUT'])
def admin_update_order(order_id):
    token = request.headers.get('X-Admin-Token', '')
    if token != ADMIN_PASS:
        return jsonify({'error':'Não autorizado'}), 403
    data = request.json
    status = data.get('status','')
    if status not in ['aprovado','reprovado']:
        return jsonify({'error':'Status inválido'}), 400

    with lock:
        for o in orders:
            if o['order_id'] == order_id:
                if o['status'] != 'pendente':
                    return jsonify({'error':'Pedido já processado'}), 400
                o['status'] = status
                if status == 'aprovado':
                    # descontar estoque
                    p = next((p for p in products if p['id']==o['product_id']), None)
                    if not p:
                        return jsonify({'error':'Produto não encontrado'}), 404
                    if p['stock'] <= 0:
                        return jsonify({'error':'Estoque insuficiente'}), 400
                    p['stock'] -= 1
                return jsonify({'success': True})
    return jsonify({'error':'Pedido não encontrado'}), 404

# Listar pedidos aprovados do usuário
@app.route('/api/orders/<user_id>', methods=['GET'])
def get_user_orders(user_id):
    with lock:
        user_orders = [o for o in orders if o['user_id']==user_id and o['status']=='aprovado']
        return jsonify(user_orders)

if __name__ == '__main__':
    app.run(debug=True)
