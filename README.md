# 🔬 LabLens

**AI-powered lab report summarizer with plain-language insights and historical biomarker trends.**

LabLens bridges the gap between complex clinical data and patient understanding. It extracts data from raw lab report PDFs (including scanned images via OCR), analyzes the biomarkers using advanced LLMs, and translates the findings into actionable, doctor-like plain-language summaries. It also tracks historical data to surface longitudinal health trends.

---

## ✨ Features

- **📄 Automated Extraction & OCR**: Upload PDF lab reports or images. Native text is extracted instantly, while scanned images are processed using Tesseract OCR.
- **🧬 Intelligent Biomarker Parsing**: Powered by Groq's blazing-fast LLaMA models, LabLens intelligently extracts individual biomarkers, values, units, and reference ranges from unstructured medical text.
- **🩺 Clinical Interpretation**: Provides easy-to-understand summaries, flags abnormal ranges, and offers general diet suggestions and medical specialist recommendations based on the findings.
- **📈 Longitudinal Trends**: Visualizes historical biomarker trajectories with interactive charts to see if a condition is improving, worsening, or stable.
- **🔐 Secure Authentication**: JWT-based authentication with bcrypt password hashing to ensure patient data remains private.

---

## 🏗️ Architecture & Tech Stack

LabLens is structured as a decoupled monorepo:

### Backend (`/backend`)
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL (production) via SQLAlchemy & asyncpg
- **AI/LLM Engine**: Groq API (`llama-3.1-8b-instant`)
- **Document Parsing**: PyMuPDF (`fitz`) and `pytesseract` (Tesseract OCR)
- **Security**: Passlib (bcrypt), python-jose (JWT)

### Frontend (`/frontend`)
- **Framework**: React 18 + Vite
- **Styling**: Custom Design System (CSS-in-JS tokens)
- **Deployment**: Configured for Vercel SPA routing (`vercel.json`)

---

## 🚀 Production Deployment

### 1. Backend (Render)
To support Optical Character Recognition (OCR) for scanned PDFs and images, the backend must be deployed using **Docker** so that system-level dependencies (Tesseract) can be installed.

1. Create a **New Web Service** on Render and connect this repository.
2. For the **Runtime**, select **Docker** (do *not* use Native Python).
3. Set the following Environment Variables:
   - `DATABASE_URL`: (Render will provide this if you attach a PostgreSQL database)
   - `LABLENS_GROQ_API_KEY`: Your Groq API key
   - `LABLENS_SECRET_KEY`: A secure random string for JWT signing
4. Render will build the image from the included `Dockerfile` and start the API.

### 2. Frontend (Vercel)
The React frontend is optimized for Vercel.

1. Import the `/frontend` directory as the root of a new Vercel project.
2. The `vercel.json` file handles React Router redirects automatically.
3. Add the following Environment Variable in Vercel:
   - `VITE_API_URL`: Your live Render API URL (e.g., `https://lablens-api.onrender.com`).

---

## 💻 Local Development

### Prerequisites
- Python 3.11+
- Node.js 18+
- Tesseract OCR (must be installed on your system for scanned PDF support)
  - Ubuntu: `sudo apt-get install tesseract-ocr`
  - macOS: `brew install tesseract`
  - Windows: [Download installer](https://github.com/UB-Mannheim/tesseract/wiki)

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
   Create a `.env` file in the `backend` directory:
   ```env
   LABLENS_GROQ_API_KEY=your_groq_api_key_here
   LABLENS_SECRET_KEY=dev-secret
   ```
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
