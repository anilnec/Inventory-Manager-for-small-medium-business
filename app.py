from flask import Flask, request, jsonify, send_file, render_template, send_from_directory
from flask_cors import CORS
import json
import os
import uuid
import datetime
import qrcode
import io
import base64
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfgen import canvas
import barcode as bc
from barcode.writer import ImageWriter

app = Flask(__name__)
CORS(app)

DATA_FILE = 'data/inventory.json'
SALES_FILE = 'data/sales.json'
SETTINGS_FILE = 'data/settings.json'

def load_data(filepath, default):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)
    return default

def save_data(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

def get_inventory():
    return load_data(DATA_FILE, [])

def get_sales():
    return load_data(SALES_FILE, [])

def get_settings():
    return load_data(SETTINGS_FILE, {
        "store_name": "My Store",
        "currency": "USD",
        "currency_symbol": "$",
        "address": "123 Main Street",
        "phone": "+1 234 567 8900",
        "email": "store@example.com",
        "tax_rate": 10,
        "receipt_footer": "Thank you for shopping with us!",
        "logo": ""
    })

# ─── ROUTES ────────────────────────────────────────────

@app.route('/')
def index():
    return send_file('templates/index.html')

@app.route('/static/<path:path>')
def static_files(path):
    return send_from_directory('static', path)

# ─── SETTINGS ──────────────────────────────────────────

@app.route('/api/settings', methods=['GET'])
def api_get_settings():
    return jsonify(get_settings())

@app.route('/api/settings', methods=['POST'])
def api_save_settings():
    settings = request.json
    save_data(SETTINGS_FILE, settings)
    return jsonify({"success": True, "message": "Settings saved"})

# ─── INVENTORY ─────────────────────────────────────────

@app.route('/api/products', methods=['GET'])
def api_get_products():
    inventory = get_inventory()
    return jsonify(inventory)

@app.route('/api/products', methods=['POST'])
def api_add_product():
    inventory = get_inventory()
    product = request.json
    product['id'] = str(uuid.uuid4())
    product['created_at'] = datetime.datetime.now().isoformat()
    product['updated_at'] = datetime.datetime.now().isoformat()
    if not product.get('barcode'):
        product['barcode'] = f"PRD{len(inventory)+1:06d}"
    inventory.append(product)
    save_data(DATA_FILE, inventory)
    return jsonify({"success": True, "product": product})

@app.route('/api/products/<product_id>', methods=['PUT'])
def api_update_product(product_id):
    inventory = get_inventory()
    for i, p in enumerate(inventory):
        if p['id'] == product_id:
            updated = {**p, **request.json}
            updated['updated_at'] = datetime.datetime.now().isoformat()
            inventory[i] = updated
            save_data(DATA_FILE, inventory)
            return jsonify({"success": True, "product": updated})
    return jsonify({"error": "Product not found"}), 404

@app.route('/api/products/<product_id>', methods=['DELETE'])
def api_delete_product(product_id):
    inventory = get_inventory()
    inventory = [p for p in inventory if p['id'] != product_id]
    save_data(DATA_FILE, inventory)
    return jsonify({"success": True})

@app.route('/api/scan/<barcode>', methods=['GET'])
def api_scan_barcode(barcode):
    inventory = get_inventory()
    for product in inventory:
        if product.get('barcode') == barcode:
            return jsonify({"found": True, "product": product})
    return jsonify({"found": False, "barcode": barcode})

@app.route('/api/products/<product_id>/qr', methods=['GET'])
def api_generate_qr(product_id):
    inventory = get_inventory()
    product = next((p for p in inventory if p['id'] == product_id), None)
    if not product:
        return jsonify({"error": "Not found"}), 404
    
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(product.get('barcode', product_id))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode()
    return jsonify({"qr": f"data:image/png;base64,{img_b64}"})

# ─── SALES ─────────────────────────────────────────────

@app.route('/api/sell', methods=['POST'])
def api_sell():
    data = request.json
    items = data.get('items', [])
    inventory = get_inventory()
    settings = get_settings()
    
    sale_items = []
    total = 0
    
    for item in items:
        product = next((p for p in inventory if p['id'] == item['product_id']), None)
        if not product:
            return jsonify({"error": f"Product {item['product_id']} not found"}), 404
        qty = item['quantity']
        if product.get('stock', 0) < qty:
            return jsonify({"error": f"Insufficient stock for {product['name']}"}), 400
        
        line_total = product['price'] * qty
        total += line_total
        sale_items.append({
            "product_id": product['id'],
            "name": product['name'],
            "barcode": product.get('barcode', ''),
            "price": product['price'],
            "quantity": qty,
            "total": line_total
        })
        
        # Deduct stock
        for i, p in enumerate(inventory):
            if p['id'] == product['id']:
                inventory[i]['stock'] = p.get('stock', 0) - qty
                inventory[i]['updated_at'] = datetime.datetime.now().isoformat()

    tax_rate = settings.get('tax_rate', 0)
    tax = total * tax_rate / 100
    grand_total = total + tax
    discount = data.get('discount', 0)
    grand_total -= discount

    sale = {
        "id": str(uuid.uuid4()),
        "invoice_no": f"INV-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
        "items": sale_items,
        "subtotal": round(total, 2),
        "tax": round(tax, 2),
        "discount": round(discount, 2),
        "total": round(grand_total, 2),
        "payment_method": data.get('payment_method', 'Cash'),
        "cashier": data.get('cashier', 'Admin'),
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    sales = get_sales()
    sales.append(sale)
    save_data(SALES_FILE, sales)
    save_data(DATA_FILE, inventory)
    
    return jsonify({"success": True, "sale": sale})

@app.route('/api/sales', methods=['GET'])
def api_get_sales():
    sales = get_sales()
    return jsonify(sales)

# ─── RECEIPT ───────────────────────────────────────────

@app.route('/api/receipt/<sale_id>', methods=['GET'])
def api_generate_receipt(sale_id):
    sales = get_sales()
    sale = next((s for s in sales if s['id'] == sale_id), None)
    if not sale:
        return jsonify({"error": "Sale not found"}), 404
    
    settings = get_settings()
    symbol = settings.get('currency_symbol', '$')
    
    buf = io.BytesIO()
    # 80mm thermal receipt width
    width = 80 * mm
    height = 200 * mm

    c = canvas.Canvas(buf, pagesize=(width, height))
    
    y = height - 10 * mm
    
    # Store name
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width/2, y, settings.get('store_name', 'My Store'))
    y -= 6 * mm
    
    c.setFont("Helvetica", 8)
    c.drawCentredString(width/2, y, settings.get('address', ''))
    y -= 5 * mm
    c.drawCentredString(width/2, y, settings.get('phone', ''))
    y -= 5 * mm
    c.drawCentredString(width/2, y, settings.get('email', ''))
    y -= 4 * mm
    
    # Separator
    c.setLineWidth(0.5)
    c.line(5*mm, y, width-5*mm, y)
    y -= 5 * mm
    
    # Invoice
    c.setFont("Helvetica-Bold", 9)
    c.drawString(5*mm, y, f"Invoice: {sale['invoice_no']}")
    y -= 5 * mm
    c.setFont("Helvetica", 8)
    dt = datetime.datetime.fromisoformat(sale['timestamp'])
    c.drawString(5*mm, y, f"Date: {dt.strftime('%d %b %Y %H:%M')}")
    y -= 5 * mm
    c.drawString(5*mm, y, f"Payment: {sale.get('payment_method','Cash')}")
    y -= 4 * mm
    c.drawString(5*mm, y, f"Cashier: {sale.get('cashier','Admin')}")
    y -= 4 * mm
    
    c.line(5*mm, y, width-5*mm, y)
    y -= 5 * mm
    
    # Header
    c.setFont("Helvetica-Bold", 8)
    c.drawString(5*mm, y, "Item")
    c.drawRightString(width-5*mm, y, "Total")
    y -= 4 * mm
    c.line(5*mm, y, width-5*mm, y)
    y -= 5 * mm
    
    # Items
    c.setFont("Helvetica", 8)
    for item in sale['items']:
        c.drawString(5*mm, y, item['name'][:22])
        c.drawRightString(width-5*mm, y, f"{symbol}{item['total']:.2f}")
        y -= 4 * mm
        c.drawString(8*mm, y, f"  {item['quantity']} x {symbol}{item['price']:.2f}")
        y -= 5 * mm
    
    c.line(5*mm, y, width-5*mm, y)
    y -= 5 * mm
    
    # Totals
    c.setFont("Helvetica", 8)
    c.drawString(5*mm, y, "Subtotal:")
    c.drawRightString(width-5*mm, y, f"{symbol}{sale['subtotal']:.2f}")
    y -= 5 * mm
    
    if sale.get('discount', 0) > 0:
        c.drawString(5*mm, y, "Discount:")
        c.drawRightString(width-5*mm, y, f"-{symbol}{sale['discount']:.2f}")
        y -= 5 * mm
    
    if sale.get('tax', 0) > 0:
        c.drawString(5*mm, y, f"Tax ({settings.get('tax_rate',0)}%):")
        c.drawRightString(width-5*mm, y, f"{symbol}{sale['tax']:.2f}")
        y -= 5 * mm
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(5*mm, y, "TOTAL:")
    c.drawRightString(width-5*mm, y, f"{symbol}{sale['total']:.2f}")
    y -= 6 * mm
    
    c.line(5*mm, y, width-5*mm, y)
    y -= 6 * mm
    
    # Footer
    c.setFont("Helvetica", 8)
    c.drawCentredString(width/2, y, settings.get('receipt_footer', 'Thank you!'))
    
    c.save()
    buf.seek(0)
    return send_file(buf, mimetype='application/pdf',
                     download_name=f"receipt_{sale['invoice_no']}.pdf",
                     as_attachment=False)

# ─── DASHBOARD ─────────────────────────────────────────

@app.route('/api/dashboard', methods=['GET'])
def api_dashboard():
    inventory = get_inventory()
    sales = get_sales()
    
    today = datetime.date.today().isoformat()
    this_month = datetime.date.today().strftime('%Y-%m')
    
    today_sales = [s for s in sales if s['timestamp'].startswith(today)]
    month_sales = [s for s in sales if s['timestamp'].startswith(this_month)]
    
    low_stock = [p for p in inventory if p.get('stock', 0) <= p.get('low_stock_alert', 5)]
    out_of_stock = [p for p in inventory if p.get('stock', 0) == 0]
    
    # Top selling products
    product_qty = {}
    for s in sales:
        for item in s['items']:
            pid = item['product_id']
            product_qty[pid] = product_qty.get(pid, 0) + item['quantity']
    
    top_products = sorted(product_qty.items(), key=lambda x: x[1], reverse=True)[:5]
    top_products_detail = []
    for pid, qty in top_products:
        p = next((x for x in inventory if x['id'] == pid), None)
        if p:
            top_products_detail.append({"name": p['name'], "quantity": qty})
    
    # Sales by day (last 7 days)
    daily_sales = {}
    for i in range(7):
        d = (datetime.date.today() - datetime.timedelta(days=i)).isoformat()
        daily_sales[d] = sum(s['total'] for s in sales if s['timestamp'].startswith(d))
    
    return jsonify({
        "total_products": len(inventory),
        "total_stock_value": sum(p.get('price', 0) * p.get('stock', 0) for p in inventory),
        "today_revenue": sum(s['total'] for s in today_sales),
        "today_transactions": len(today_sales),
        "month_revenue": sum(s['total'] for s in month_sales),
        "month_transactions": len(month_sales),
        "low_stock_count": len(low_stock),
        "out_of_stock_count": len(out_of_stock),
        "low_stock_products": low_stock[:5],
        "top_products": top_products_detail,
        "daily_sales": daily_sales,
        "total_sales": len(sales),
        "total_revenue": sum(s['total'] for s in sales)
    })

if __name__ == '__main__':
    os.makedirs('data', exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)
