# YourShop - Retail Management System

A web-based retail shop management system built with Flask.

## 🚀 Live Demo

👉 [https://yourshop-3.onrender.com](https://yourshop-3.onrender.com/login?next=%2F)

## Features

- 🔐 User authentication with role-based access (Admin, Manager, Staff)
- 🏪 Multi-branch support
- 📦 Inventory management
- 🧾 Billing system
- 👥 Customer management
- 🏭 Supplier management
- 💳 Payment integration (Razorpay)
- 📊 Reports and analytics
- 📧 Email notifications (Flask-Mail)
- 📱 SMS notifications (Twilio)
- 🏷️ Barcode generation
- 📄 PDF report generation

## Tech Stack

- **Backend:** Python, Flask
- **Database:** MySQL
- **ORM:** SQLAlchemy + Flask-Migrate
- **Authentication:** Flask-Login
- **Frontend:** Jinja2 Templates, CSS
- **Deployment:** Render

## Project Structure

yourshop/
├── app/
│   ├── models/          # Database models
│   ├── routes/          # Blueprint routes
│   ├── services/        # Business logic
│   ├── static/css/      # Stylesheets
│   └── templates/       # HTML templates
├── requirements.txt
└── render.yaml

## Setup & Installation

### Local Development

1. Clone the repo:
```bash
git clone https://github.com/kain240/yourshop.git
cd yourshop
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root:

5. Run the app:
```bash
flask run
```

## Deployment

This project is deployed on [Render](https://render.com).

Live URL: https://yourshop-3.onrender.com

## Environment Variables

| Variable | Description |
|---|---|
| `SECRET_KEY` | Flask secret key |
| `DATABASE_URL` | MySQL connection string |
| `MAIL_USERNAME` | Email for notifications |
| `MAIL_PASSWORD` | Email password |


