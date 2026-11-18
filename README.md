# India Smart Irrigation Planner (AgriSaathi)

An AI-powered smart irrigation planning web application built with **Flask**, **scikit-learn**, **Google Gemini**, **Open-Meteo Live Weather**, and **W3C WebAuthn Passkeys** for Indian farmers across all 36 States and Union Territories.

## Key Features

- **State & Crop-Specific ML Predictions**: Hybrid RandomForest + Indian state-wise agronomic irrigation rules (`India_State_Crop_Irrigation_Ranges.csv`, `irrigation_model.joblib`).
- **Multi-Farmer & Land Section Management**: Farmer onboarding, multiple farm plots/sections, automated irrigation schedules, and unified calendar tracking backed by SQLite.
- **AgriSaathi AI Assistant**: Context-aware agricultural chatbot powered by Google Gemini (`google-genai`) with tool-calling support.
- **Multilingual & Voice Interface**: Supports 23 Indian and global languages (`data/translations/`) with voice commands and speech synthesis.
- **Passwordless Biometric Login**: W3C WebAuthn / FIDO2 passkeys (Face ID, fingerprint, Windows Hello) plus mobile OTP fallback.
- **Live Weather Integration**: Real-time weather and rainfall forecasting via Open-Meteo.
- **Super Admin Portal**: Centralized monitoring, farmer management, audit logging, and AI/system health diagnostics (`/admin`).

## Project Structure

```text
India-Smart-Irrigation/
├── app.py                                           # Main Flask application & API endpoints
├── train_irrigation_model.py                        # ML pipeline training script
├── irrigation_model.joblib                          # Pre-trained RandomForest model
├── India_State_Crop_Irrigation_Ranges.csv           # State-wise crop irrigation thresholds
├── India_State_Crop_Irrigation_ML_Training_Dataset.csv
├── requirements.txt                                 # Python dependencies
├── render.yaml                                      # Render Blueprint deployment config
├── Procfile                                         # Gunicorn production start command
├── .env.example                                     # Environment variables template
├── src/                                             # Backend services (ML, auth, AI, weather, voice, admin)
├── templates/                                       # Jinja2 HTML templates
├── static/                                          # Frontend JS and CSS assets
├── data/                                            # Datasets and 23 language translation files
├── models/                                          # Crop-specific ML models and metrics
└── tests/                                           # Pytest unit and integration test suite
```

## Local Setup

1. **Create and activate a virtual environment** (Python 3.11+ recommended):
   ```bash
   python -m venv .venv
   # Windows (PowerShell):
   .venv\Scripts\Activate.ps1
   # macOS / Linux:
   source .venv/bin/activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and add your `GEMINI_API_KEY` (from [Google AI Studio](https://aistudio.google.com/app/apikey)) and admin credentials.

4. **Run the application**:
   ```bash
   python app.py
   ```
   Open [http://localhost:5000](http://localhost:5000) in your browser.

5. **Run tests**:
   ```bash
   pytest
   ```

## Deploying to Render

This repository is pre-configured for **Render** via `render.yaml` and `Procfile`.

### Option 1: One-Click Blueprint Deploy (Recommended)
1. Push this repository to your GitHub account.
2. Go to [Render Dashboard](https://dashboard.render.com/) -> **New +** -> **Blueprint**.
3. Connect your GitHub repository and select `India-Smart-Irrigation`.
4. Render will automatically detect `render.yaml` and configure:
   - **Runtime**: Python `3.11.9`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120`
   - **Health Check Path**: `/health`
5. Fill in the prompted environment variables:
   - `GEMINI_API_KEY`: Your Google Gemini API key (required for AgriSaathi chatbot)
   - `ADMIN_USERNAME` / `ADMIN_EMAIL` / `ADMIN_PASSWORD`: Your Super Admin login credentials
   - `WEBAUTHN_RP_ID`: Your Render domain (e.g., `india-smart-irrigation.onrender.com`)
   - `WEBAUTHN_ORIGIN`: Your Render URL (e.g., `https://india-smart-irrigation.onrender.com`)
6. Click **Apply** to deploy.

### Option 2: Manual Web Service on Render
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120`
- **Health Check Path**: `/health`
- Set `PYTHON_VERSION=3.11.9`, `FLASK_ENV=production`, `FLASK_SECRET_KEY`, and `GEMINI_API_KEY` in Environment Variables.

> **Note on Render Free Tier:** Free Render web services use an ephemeral filesystem, so SQLite data (`data/irrigation_schedules.db`) resets on redeploy or restart. For persistent production storage, attach a Render Persistent Disk mounted at `/opt/render/project/src/data`.
