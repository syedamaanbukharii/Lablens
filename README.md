# 🔬 LabLens

**AI-powered lab report summarizer with plain-language insights and historical biomarker trends.**

LabLens bridges the gap between complex clinical data and patient understanding. It extracts data from raw lab report PDFs, analyzes the biomarkers against standard reference ranges, and translates the findings into actionable, doctor-like plain-language summaries. It also tracks historical data to surface longitudinal health trends.

---

## ✨ Features

- **📄 Automated Extraction**: Upload PDF lab reports and automatically extract raw text and metrics.
- **🧬 Biomarker Parsing**: Deterministically parses individual biomarkers, values, units, and reference ranges.
- **🩺 Clinical Interpretation**: Analyzes current values against historical data to determine if a patient's health is improving, worsening, or stable—accounting for whether a "lower" or "higher" value is clinically beneficial.
- **📈 Longitudinal Trends**: Visualizes historical biomarker trajectories with interactive charts.
- **🔐 Secure Authentication**: JWT-based authentication with bcrypt password hashing to ensure patient data remains private.

---

## 🏗️ Architecture & Tech Stack

LabLens is structured as a decoupled monorepo:

### Backend (`/backend`)
- **Framework**: FastAPI (Python 3.11+)
- **Database**: SQLite (local) / PostgreSQL (production) via SQLAlchemy & asyncpg/aiosqlite
- **AI/Extraction**: PyMuPDF for document parsing
- **Security**: Passlib (bcrypt), python-jose (JWT)

### Frontend (`/frontend`)
- **Framework**: React 18 + Vite
- **Styling**: Custom Design System (CSS-in-JS tokens)
- **Deployment**: Configured for Vercel SPA routing (`vercel.json`)

---

## 🚀 Production Deployment

This repository is pre-configured for automated Infrastructure-as-Code (IaC) deployment to **Render** and **Vercel**.

### 1. Backend (Render)
The backend service and PostgreSQL database can be deployed instantly using the provided `render.yaml` Blueprint.
1. Connect this repository to your Render account.
2. Render will automatically spin up the `lablens-db` (PostgreSQL) and `lablens-api` (Python web service).
3. The API will be available at your Render URL.

### 2. Frontend (Vercel)
The React frontend is optimized for Vercel.
1. Import the `/frontend` directory as the root of a new Vercel project.
2. The `vercel.json` file handles React Router redirects.
3. Add the following Environment Variable in Vercel:
   - `VITE_API_URL`: Your live Render API URL (e.g., `https://lablens-api-xyz.onrender.com`).

---

## 💻 Local Development

### Prerequisites
- Python 3.11+
- Node.js 18+

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/syedamaanbukharii/Lablens.git
   cd Lablens
   ```

2. **Backend Setup**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e .[dev]
   ```
   Create a `.env` file in the `backend` directory (refer to `.env.example`).
   Run the development server:
   ```bash
   uvicorn lablens.api.main:app --reload
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

---

## 🔒 Security Notes
- Database IDs utilize cryptographically secure URL-safe tokens to prevent enumeration and collision attacks.
- Passwords are never logged or stored in plain text.
- CORS is strictly managed in production via environment variables.

---

*Built for a clearer, healthier future.*
