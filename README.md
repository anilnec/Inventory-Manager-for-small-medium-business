# StockMaster Pro 📦
### Full-Stack Inventory Management System

A modern, mobile-ready inventory system with barcode/QR scanner, POS, receipts, and dashboard.

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the server
```bash
python app.py
```

### 3. Open in browser
```
http://localhost:5000
```
For mobile access on the same network:
```
http://<YOUR_IP>:5000
```

---

## ✨ Features

| Feature | Description |
|---|---|
| 📊 Dashboard | Revenue charts, top products, stock alerts |
| 🛒 Point of Sale | Grid product picker, cart, discount, tax |
| 📷 Barcode/QR Scanner | Camera scanner (mobile/desktop) + manual entry |
| 📦 Inventory | Add, edit, delete products with full details |
| 🧾 Receipts | PDF thermal receipt generation & printing |
| ⚠️ Low Stock Alerts | Automatic alerts with configurable thresholds |
| 📈 Sales History | Full sales log with date filtering |
| 💱 Multi-Currency | USD, EUR, GBP, INR, JPY, AED and more |
| 🏪 Store Branding | Logo, store name, address on receipts |
| 📱 Mobile-Ready | Camera scanner works on phone browsers |

---

## 📱 Mobile Usage

1. Connect your phone to the same WiFi network
2. Find your computer's local IP (`ipconfig` / `ifconfig`)
3. Open `http://<IP>:5000` on your phone browser
4. Go to **Scanner** → **Start Camera** to use phone camera

---

## 🗂 Project Structure

```
inventory-system/
├── app.py              # Flask backend + all API routes
├── requirements.txt    # Python dependencies
├── templates/
│   └── index.html      # Full frontend (single-page app)
├── data/
│   ├── inventory.json  # Product data
│   ├── sales.json      # Sales records
│   └── settings.json   # Store configuration
└── README.md
```

---

## 🔌 API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/products` | List all products |
| POST | `/api/products` | Add product |
| PUT | `/api/products/<id>` | Update product |
| DELETE | `/api/products/<id>` | Delete product |
| GET | `/api/scan/<barcode>` | Lookup by barcode |
| GET | `/api/products/<id>/qr` | Generate QR code |
| POST | `/api/sell` | Record a sale |
| GET | `/api/sales` | Sales history |
| GET | `/api/receipt/<id>` | Generate PDF receipt |
| GET | `/api/dashboard` | Dashboard stats |
| GET/POST | `/api/settings` | Get/save settings |

---

## ⚙️ First-Time Setup

1. Go to **Settings** in the sidebar
2. Set your store name, address, phone, email
3. Upload your logo
4. Choose your currency and tax rate
5. Customize receipt footer message
6. Go to **Add Product** to add your inventory

---

## 🖨 Receipt Format

Receipts are generated as **80mm thermal printer** compatible PDFs.
Print via: `File → Print → Change paper size to custom 80mm`
Or send directly to a thermal POS printer.
