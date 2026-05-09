from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import datetime, timedelta
from pathlib import Path
from db import db
from models import User, Product, Transaction, Customer, ActivityLog
from auth.decorators import login_required , log_activity , management_required , manager_required

app = Flask(__name__, template_folder='Templates',
            static_folder='Templates/static')
app.secret_key = 'pos-inventory-secret-key-2026'
db_path = Path(app.root_path) / 'instance' / 'pos_system.db'
db_path.parent.mkdir(exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path.as_posix()}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)



@app.route('/')
def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            if user.role == 'admin':
                return redirect(url_for('dashboard'))
            if user.role == 'manager':
                return redirect(url_for('manager_dashboard'))
            return redirect(url_for('pos'))
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            return render_template('login.html', error='Username and password required')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            if not user.is_active:
                return render_template('login.html', error='Your account is inactive. Please contact admin.')
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            session['login_time'] = datetime.now().strftime(
                '%Y-%m-%d %H:%M:%S')
            log_activity(user.id, 'LOGIN', f'{user.username} logged in')

            if user.role == 'admin':
                return redirect(url_for('dashboard'))
            if user.role == 'manager':
                return redirect(url_for('manager_dashboard'))
            return redirect(url_for('pos'))
        else:
            return render_template('login.html', error='Invalid username or password')

    return render_template('login.html')


@app.route('/logout')
def logout():
    if 'user_id' in session:
        log_activity(session['user_id'], 'LOGOUT',
                     f"{session.get('username', 'User')} logged out")
    session.clear()
    return redirect(url_for('login'))

# ==================== ADMIN DASHBOARD ROUTES ====================


@app.route('/dashboard')
@management_required
def dashboard():
    user = User.query.get(session.get('user_id'))
    username = user.username if user else 'Admin'
    login_time = session.get('login_time', 'N/A')

    # Calculate stats from database
    total_products = Product.query.count()
    total_quantity = db.session.query(
        db.func.sum(Product.quantity)).scalar() or 0
    total_sales = db.session.query(db.func.count(Transaction.id)).scalar() or 0
    total_revenue = db.session.query(
        db.func.sum(Transaction.total_amount)).scalar() or 0.0
    low_stock_alerts = Product.query.filter(
        Product.quantity.between(0, 5)).count()

    stats = {
        'total_products': total_products,
        'total_stock': total_quantity,
        'total_sales': total_sales,
        'total_revenue': float(total_revenue),
        'low_stock_alerts': low_stock_alerts
    }

    return render_template('dashboard.html', username=username, stats=stats, login_time=login_time)


@app.route('/manager')
@manager_required
def manager_dashboard():
    user = User.query.get(session.get('user_id'))
    username = user.username if user else 'Manager'
    login_time = session.get('login_time', 'N/A')

    total_products = Product.query.count()
    total_quantity = db.session.query(
        db.func.sum(Product.quantity)).scalar() or 0
    total_sales = db.session.query(db.func.count(Transaction.id)).scalar() or 0
    total_revenue = db.session.query(
        db.func.sum(Transaction.total_amount)).scalar() or 0.0
    low_stock_alerts = Product.query.filter(
        Product.quantity.between(0, 5)).count()

    stats = {
        'total_products': total_products,
        'total_stock': total_quantity,
        'total_sales': total_sales,
        'total_revenue': float(total_revenue),
        'low_stock_alerts': low_stock_alerts
    }

    return render_template('manager.html', username=username, stats=stats, login_time=login_time)


@app.route('/manage-users')
@management_required
def manage_users_page():
    return render_template('manageUsers.html')


@app.route('/api/users', methods=['GET'])
@management_required
def get_users():
    users = User.query.order_by(User.id.asc()).all()
    return jsonify([u.to_dict() for u in users])


@app.route('/api/users', methods=['POST'])
@management_required
def create_user():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    role = data.get('role', '').strip().lower()
    full_name = data.get('full_name', '').strip()

    if not username or not password or not role:
        return jsonify({'error': 'Username, password and role are required'}), 400

    if role not in ('admin', 'manager', 'cashier'):
        return jsonify({'error': 'Invalid role selected'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 400

    user = User(
        username=username,
        role=role,
        full_name=full_name if full_name else None,
        is_active=True
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify(user.to_dict()), 201


@app.route('/api/users/<int:user_id>', methods=['PUT'])
@management_required
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}

    if 'username' in data:
        new_username = data.get('username', '').strip()
        if not new_username:
            return jsonify({'error': 'Username cannot be empty'}), 400
        existing = User.query.filter_by(username=new_username).first()
        if existing and existing.id != user.id:
            return jsonify({'error': 'Username already exists'}), 400
        user.username = new_username

    if 'password' in data:
        new_password = data.get('password', '').strip()
        if not new_password:
            return jsonify({'error': 'Password cannot be empty'}), 400
        user.set_password(new_password)

    if 'role' in data:
        # Role changes are not allowed through this endpoint
        pass

    if 'full_name' in data:
        user.full_name = data.get('full_name', '').strip() or None

    if 'active' in data:
        new_active = bool(data.get('active'))
        if user.id == session.get('user_id') and not new_active:
            return jsonify({'error': 'You cannot deactivate your own account'}), 400
        user.is_active = new_active

    db.session.commit()
    return jsonify(user.to_dict())


@app.route('/api/users/<int:user_id>/change-password', methods=['PUT'])
@management_required
def change_user_password(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}

    current_password = data.get('current_password', '').strip()
    new_password = data.get('new_password', '').strip()

    if not current_password or not new_password:
        return jsonify({'error': 'Current and new password are required'}), 400

    if not user.check_password(current_password):
        return jsonify({'error': 'Current password is incorrect'}), 400

    user.set_password(new_password)
    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@management_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.id == session.get('user_id'):
        return jsonify({'error': 'You cannot remove your own account'}), 400

    if user.role == 'admin':
        admin_count = User.query.filter_by(role='admin').count()
        if admin_count <= 1:
            return jsonify({'error': 'At least one admin account must remain'}), 400

    db.session.delete(user)
    db.session.commit()
    return '', 204


@app.route('/api/customers', methods=['GET'])
@login_required
def get_customers():
    customers = Customer.query.all()
    return jsonify([c.to_dict() for c in customers])


@app.route('/api/customers', methods=['POST'])
@login_required
def create_customer():
    data = request.get_json()
    if not all(k in data for k in ['name', 'phone']):
        return jsonify({'error': 'Name and phone are required'}), 400

    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip()

    if not name or not phone:
        return jsonify({'error': 'Name and phone cannot be empty'}), 400

    # Check if phone already exists
    existing = Customer.query.filter_by(phone=phone).first()
    if existing:
        return jsonify({'error': 'Customer with this phone number already exists'}), 400

    customer = Customer(name=name, phone=phone)
    db.session.add(customer)
    db.session.commit()
    return jsonify(customer.to_dict()), 201


@app.route('/api/customers/<int:customer_id>', methods=['PUT'])
@login_required
def update_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    data = request.get_json()

    if 'name' in data:
        new_name = data.get('name', '').strip()
        if not new_name:
            return jsonify({'error': 'Name cannot be empty'}), 400
        customer.name = new_name

    if 'phone' in data:
        new_phone = data.get('phone', '').strip()
        if not new_phone:
            return jsonify({'error': 'Phone cannot be empty'}), 400
        existing = Customer.query.filter_by(phone=new_phone).first()
        if existing and existing.id != customer.id:
            return jsonify({'error': 'Phone number already exists'}), 400
        customer.phone = new_phone

    db.session.commit()
    return jsonify(customer.to_dict())


@app.route('/api/customers/<int:customer_id>', methods=['DELETE'])
@login_required
def delete_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    db.session.delete(customer)
    db.session.commit()
    return '', 204


@app.route('/api/customers/search/<query>')
@login_required
def search_customers(query):
    customers = Customer.query.filter(
        (Customer.name.ilike(f'%{query}%')) |
        (Customer.phone.ilike(f'%{query}%'))
    ).all()
    return jsonify([c.to_dict() for c in customers])

# ==================== PRODUCT MANAGEMENT API ====================


@app.route('/api/products', methods=['GET'])
@management_required
def get_products():
    products = Product.query.all()
    return jsonify([p.to_dict() for p in products])


@app.route('/api/cashiers', methods=['GET'])
@management_required
def get_cashiers():
    cashiers = User.query.filter_by(role='cashier').all()
    return jsonify([c.to_dict() for c in cashiers])


@app.route('/api/cashiers', methods=['POST'])
@management_required
def create_cashiers():
    data = request.get_json()
    if not all(k in data for k in ['username', 'password']):
        return jsonify({'error': 'Missing required fields'})

    if User.query.filter_by(role='cashier', username=data['username']).first():
        return jsonify({'error': 'Cashier with this username already exist!'})

    cashier = User(
        username=data['username'],
        role='cashier',
    )

    cashier.set_password(data['password'])

    db.session.add(cashier)
    db.session.commit()

    cashiers = User.query.filter_by(role='cashier').all()
    return jsonify([c.to_dict() for c in cashiers])


@app.route('/api/cashiers/<int:cashier_id>', methods=['GET'])
@management_required
def get_cashier(cashier_id):
    cashier = User.query.filter_by(role='cashier', id=cashier_id).first()
    print(cashier)

    if cashier:
        return jsonify(cashier.to_dict())

    return jsonify({'error': 'Cashier not found!'})


@app.route('/api/cashiers/<int:cashier_id>', methods=['PUT'])
@management_required
def update_cashier(cashier_id):
    cashier = User.query.filter_by(role='cashier', id=cashier_id).first()
    if not cashier:
        return jsonify({'error': 'Cashier not found!'})
    data = request.get_json()

    cashier.username = data.get('username', cashier.username)
    if data.get('password', None):
        cashier.set_password(data.get('password'))

    db.session.commit()
    return jsonify(cashier.to_dict())


@app.route('/api/cashiers/<int:cashier_id>', methods=['DELETE'])
@management_required
def delete_cashier(cashier_id):
    cashier = User.query.filter_by(role='cashier', id=cashier_id).first()
    print(cashier)

    if cashier:
        db.session.delete(cashier)
        db.session.commit()
        return '', 204

    return jsonify({'error': 'Cashier not found!'})


@app.route('/api/managers', methods=['GET'])
@management_required
def get_managers():
    managers = User.query.filter_by(role='manager').all()
    return jsonify([m.to_dict() for m in managers])


@app.route('/api/managers', methods=['POST'])
@management_required
def create_manager():
    data = request.get_json()
    if not all(k in data for k in ['username', 'password']):
        return jsonify({'error': 'Missing required fields'})

    if User.query.filter_by(role='manager', username=data['username']).first():
        return jsonify({'error': 'Manager with this username already exist!'})

    manager = User(
        username=data['username'],
        role='manager',
    )

    manager.set_password(data['password'])

    db.session.add(manager)
    db.session.commit()

    managers = User.query.filter_by(role='manager').all()
    return jsonify([m.to_dict() for m in managers])


@app.route('/api/managers/<int:manager_id>', methods=['GET'])
@management_required
def get_manager(manager_id):
    manager = User.query.filter_by(role='manager', id=manager_id).first()

    if manager:
        return jsonify(manager.to_dict())

    return jsonify({'error': 'Manager not found!'})


@app.route('/api/managers/<int:manager_id>', methods=['PUT'])
@management_required
def update_manager(manager_id):
    manager = User.query.filter_by(role='manager', id=manager_id).first()
    if not manager:
        return jsonify({'error': 'Manager not found!'})
    data = request.get_json()

    manager.username = data.get('username', manager.username)
    if data.get('password', None):
        manager.set_password(data.get('password'))

    db.session.commit()
    return jsonify(manager.to_dict())


@app.route('/api/managers/<int:manager_id>', methods=['DELETE'])
@management_required
def delete_manager(manager_id):
    manager = User.query.filter_by(role='manager', id=manager_id).first()

    if manager:
        db.session.delete(manager)
        db.session.commit()
        return '', 204

    return jsonify({'error': 'Manager not found!'})


@app.route('/api/products', methods=['POST'])
@management_required
def create_product():
    data = request.get_json()

    # Validation
    if not all(k in data for k in ['name', 'barcode', 'price', 'quantity']):
        return jsonify({'error': 'Missing required fields'}), 400

    if Product.query.filter_by(barcode=data['barcode']).first():
        return jsonify({'error': 'Barcode already exists'}), 400

    product = Product(
        name=data['name'],
        barcode=data['barcode'],
        price=int(data['price']),
        quantity=int(data['quantity']),
        category=data.get('category', 'General')
    )

    db.session.add(product)
    db.session.commit()

    return jsonify(product.to_dict()), 201


@app.route('/api/products/<int:product_id>', methods=['GET'])
@management_required
def get_product(product_id):
    product = Product.query.get_or_404(product_id)
    return jsonify(product.to_dict())


@app.route('/api/products/<int:product_id>', methods=['PUT'])
@management_required
def update_product(product_id):
    product = Product.query.get_or_404(product_id)
    data = request.get_json()

    product.name = data.get('name', product.name)
    product.price = int(data.get('price', product.price))
    product.quantity = int(data.get('quantity', product.quantity))
    product.category = data.get('category', product.category)

    db.session.commit()
    return jsonify(product.to_dict())


@app.route('/api/products/<int:product_id>', methods=['DELETE'])
@management_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)

    # Check if product has been sold
    sold_transaction = Transaction.query.all()
    for transaction in sold_transaction:
        items = transaction.items
        if any(item['id'] == product_id for item in items):
            return jsonify({'error': 'Cannot delete product that has been sold'}), 400

    db.session.delete(product)
    db.session.commit()
    return '', 204


@app.route('/api/products/search/<query>')
@management_required
def search_products(query):
    products = Product.query.filter(
        (Product.name.ilike(f'%{query}%')) |
        (Product.barcode.ilike(f'%{query}%'))
    ).all()
    return jsonify([p.to_dict() for p in products])


@app.route('/api/products/low-stock')
@management_required
def get_low_stock_products():
    # Get products with quantity <= 5
    products = Product.query.filter(Product.quantity <= 5).all()
    return jsonify([p.to_dict() for p in products])

# ==================== POS INTERFACE ROUTES ====================


@app.route('/pos')
@login_required
def pos():
    username = session.get('username', 'Cashier')
    return render_template('pos.html', username=username)


@app.route('/api/pos/products')
@login_required
def pos_get_products():
    products = Product.query.filter(Product.quantity > 0).all()
    return jsonify([p.to_dict() for p in products])


@app.route('/api/pos/search/<query>')
@login_required
def pos_search_products(query):
    products = Product.query.filter(
        (Product.name.ilike(f'%{query}%')) |
        (Product.barcode.ilike(f'%{query}%'))
    ).filter(Product.quantity > 0).all()
    return jsonify([p.to_dict() for p in products])


@app.route('/api/transactions/checkout', methods=['POST'])
@login_required
def checkout():
    data = request.get_json(silent=True) or {}
    items_payload = data.get('items', [])
    discount_percent_raw = data.get('discount_percent', 0)
    customer_id = data.get('customer_id')

    if not isinstance(items_payload, list) or not items_payload:
        return jsonify({'error': 'No items in cart'}), 400

    try:
        discount_percent = float(discount_percent_raw)
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid discount value'}), 400

    discount_percent = max(0.0, min(discount_percent, 100.0))

    # Validate customer_id if provided
    if customer_id is not None:
        try:
            customer_id = int(customer_id)
            customer = Customer.query.get(customer_id)
            if not customer:
                return jsonify({'error': 'Customer not found'}), 404
        except (TypeError, ValueError):
            return jsonify({'error': 'Invalid customer ID'}), 400
    else:
        customer_id = None

    try:
        subtotal = 0.0
        tax = 0.0
        processed_items = []

        for row in items_payload:
            if not isinstance(row, dict):
                continue

            try:
                product_id = int(row.get('id'))
                quantity = int(row.get('quantity', 0))
            except (TypeError, ValueError):
                return jsonify({'error': 'Invalid item data'}), 400

            if quantity <= 0:
                return jsonify({'error': 'Item quantity must be at least 1'}), 400

            product = Product.query.get(product_id)
            if not product:
                return jsonify({'error': f'Product not found (ID: {product_id})'}), 404

            if product.quantity < quantity:
                return jsonify({'error': f'Insufficient stock for {product.name}. Available: {product.quantity}'}), 400

            line_price = int(product.price)
            line_total = line_price * quantity
            subtotal += line_total
            processed_items.append({
                'id': product.id,
                'name': product.name,
                'price': round(line_price, 2),
                'quantity': quantity,
                'line_total': round(line_total, 2)
            })

        if not processed_items:
            return jsonify({'error': 'No valid items in cart'}), 400

        discount_amount = subtotal * (discount_percent / 100.0)
        total = max(subtotal + tax - discount_amount, 0.0)

        transaction = Transaction(
            cashier_id=session['user_id'],
            customer_id=customer_id,
            total_amount=round(total),
            items_count=len(processed_items),
            items=processed_items
        )
        db.session.add(transaction)

        for item in processed_items:
            product = Product.query.get(item['id'])
            if product:
                product.quantity -= item['quantity']
                if product.quantity < 0:
                    product.quantity = 0

        db.session.commit()
        log_activity(
            session['user_id'],
            'SALE',
            f"Sale #{transaction.id} - {len(processed_items)} item(s) - ${float(total):.2f}"
        )

        return jsonify({
            'success': True,
            'receipt_id': transaction.id,
            'message': 'Transaction recorded successfully',
            'timestamp': transaction.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'subtotal': round(subtotal, 2),
            'tax': round(tax, 2),
            'discount_percent': round(discount_percent, 2),
            'discount_amount': round(discount_amount, 2),
            'total': round(total, 2)
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==================== ADMIN REPORTS ====================


@app.route('/api/sales/history')
@management_required
def sales_history():
    transactions = Transaction.query.order_by(
        Transaction.created_at.desc()).limit(100).all()
    return jsonify([t.to_dict() for t in transactions])


@app.route('/api/sales/stats')
@management_required
def sales_stats():
    # Sales by day for the last 7 days
    today = datetime.utcnow().date()
    sales_data = []
    labels = []

    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        count = Transaction.query.filter(
            db.func.date(Transaction.created_at) == date
        ).count()
        sales_data.append(count)
        labels.append(date.strftime('%a'))

    return jsonify({
        'sales': sales_data,
        'labels': labels
    })


@app.route('/api/sales/monthly-summary')
@management_required
def sales_monthly_summary():
    now = datetime.utcnow()
    current_month_index = now.year * 12 + (now.month - 1)
    month_keys = []
    labels = []

    for i in range(11, -1, -1):
        month_index = current_month_index - i
        year = month_index // 12
        month = (month_index % 12) + 1
        month_keys.append(f'{year:04d}-{month:02d}')
        labels.append(datetime(year, month, 1).strftime('%b'))

    rows = db.session.query(
        db.func.strftime('%Y-%m', Transaction.created_at).label('month_key'),
        db.func.count(Transaction.id).label('transaction_count'),
        db.func.coalesce(db.func.sum(Transaction.total_amount),
                         0.0).label('revenue')
    ).group_by('month_key').all()

    summary_map = {
        row.month_key: {
            'transactions': int(row.transaction_count or 0),
            'revenue': float(row.revenue or 0.0)
        }
        for row in rows
    }

    monthly_transactions = []
    monthly_revenue = []
    for key in month_keys:
        month_data = summary_map.get(key, {'transactions': 0, 'revenue': 0.0})
        monthly_transactions.append(month_data['transactions'])
        monthly_revenue.append(round(month_data['revenue'], 2))

    return jsonify({
        'labels': labels,
        'monthKeys': month_keys,
        'transactions': monthly_transactions,
        'revenue': monthly_revenue
    })


@app.route('/api/sales/monthly-detail/<month_key>')
@management_required
def sales_monthly_detail(month_key):
    try:
        year, month = map(int, month_key.split('-'))
    except ValueError:
        return jsonify({'error': 'Invalid month key'}), 400

    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)

    transactions = Transaction.query.filter(
        Transaction.created_at >= start,
        Transaction.created_at < end
    ).order_by(Transaction.created_at.desc()).all()

    result = []
    for t in transactions:
        cashier = User.query.get(t.cashier_id)
        result.append({
            'id': t.id,
            'cashier': cashier.username if cashier else 'Unknown',
            'items_count': t.items_count,
            'items': t.items,
            'total_amount': float(t.total_amount),
            'created_at': t.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })

    return jsonify(result)


# ==================== MANAGER MONITOR API ====================


@app.route('/api/monitor/summary')
@management_required
def monitor_summary():
    today = datetime.utcnow().date()

    total_sales_today = Transaction.query.filter(
        db.func.date(Transaction.created_at) == today
    ).count()

    total_revenue_today = db.session.query(
        db.func.sum(Transaction.total_amount)
    ).filter(db.func.date(Transaction.created_at) == today).scalar() or 0.0

    total_cashiers = User.query.filter_by(role='cashier').count()

    low_stock_alerts = Product.query.filter(
        Product.quantity.between(0, 5)
    ).count()

    return jsonify({
        'total_sales_today': total_sales_today,
        'total_revenue_today': round(float(total_revenue_today), 2),
        'total_cashiers': total_cashiers,
        'low_stock_alerts': low_stock_alerts
    })


@app.route('/api/monitor/cashiers')
@management_required
def monitor_cashiers():
    days = request.args.get('days', 1, type=int)
    _since = datetime.utcnow() - timedelta(days=days)
    today = datetime.utcnow().date()

    cashiers = User.query.filter_by(role='cashier').all()
    result = []
    for c in cashiers:
        # Always show today's stats in the summary cards
        today_txns = Transaction.query.filter(
            Transaction.cashier_id == c.id,
            db.func.date(Transaction.created_at) == today
        ).all()
        today_sales = len(today_txns)
        today_revenue = sum(float(t.total_amount or 0) for t in today_txns)
        result.append({
            'id': c.id,
            'username': c.username,
            'is_active': bool(c.is_active),
            'today_sales': today_sales,
            'today_revenue': round(today_revenue, 2)
        })
    return jsonify(result)


@app.route('/api/monitor/cashier/<int:cashier_id>/sales')
@management_required
def monitor_cashier_sales(cashier_id):
    days = request.args.get('days', 7, type=int)
    since = datetime.utcnow() - timedelta(days=days)
    txns = Transaction.query.filter(
        Transaction.cashier_id == cashier_id,
        Transaction.created_at >= since
    ).order_by(Transaction.created_at.desc()).all()

    return jsonify([{
        'sale_id': t.id,
        'items_count': t.items_count,
        'total': float(t.total_amount),
        'date': t.created_at.strftime('%Y-%m-%d %H:%M:%S')
    } for t in txns])


@app.route('/api/monitor/cashier/<int:cashier_id>/logs')
@management_required
def monitor_cashier_logs(cashier_id):
    logs = ActivityLog.query.filter_by(user_id=cashier_id)\
        .order_by(ActivityLog.timestamp.desc()).limit(50).all()
    return jsonify([l.to_dict() for l in logs])

# ==================== INITIALIZATION ====================


def init_db():
    """Initialize database with sample data if empty"""
    with app.app_context():
        db.create_all()
        user_columns = [row[1] for row in db.session.execute(
            db.text('PRAGMA table_info(user)')).fetchall()]
        transaction_columns = [row[1] for row in db.session.execute(
            db.text('PRAGMA table_info("transaction")')).fetchall()]

        if 'full_name' not in user_columns:
            db.session.execute(db.text(
                'ALTER TABLE user ADD COLUMN full_name VARCHAR(120)'))
            db.session.commit()

        if 'is_active' not in user_columns:
            db.session.execute(db.text(
                'ALTER TABLE user ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1'))
            db.session.commit()

        if 'customer_id' not in transaction_columns:
            db.session.execute(db.text(
                'ALTER TABLE "transaction" ADD COLUMN customer_id INTEGER REFERENCES customer(id)'))
            db.session.commit()

        # Ensure default users always exist
        if not User.query.filter_by(username='admin').first():
            admin_user = User(username='admin', role='admin')
            admin_user.set_password('admin123')
            db.session.add(admin_user)

        if not User.query.filter_by(username='manager').first():
            manager_user = User(username='manager', role='manager')
            manager_user.set_password('manager123')
            db.session.add(manager_user)

        if not User.query.filter_by(username='cashier').first():
            cashier_user = User(username='cashier', role='cashier')
            cashier_user.set_password('cashier123')
            db.session.add(cashier_user)

        db.session.commit()

        # Create sample products if empty
        if Product.query.count() == 0:
            sample_products = [
                Product(name='Laptop', barcode='001', price=999.99,
                        quantity=10, category='Electronics'),
                Product(name='Mouse', barcode='002', price=29.99,
                        quantity=50, category='Electronics'),
                Product(name='Keyboard', barcode='003', price=79.99,
                        quantity=30, category='Electronics'),
                Product(name='Monitor', barcode='004', price=299.99,
                        quantity=15, category='Electronics'),
                Product(name='USB Cable', barcode='005', price=9.99,
                        quantity=100, category='Accessories'),
            ]
            for product in sample_products:
                db.session.add(product)
            db.session.commit()
            print("✓ Sample products created")


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5555)
