# 🚗 Vehicle Undercarriage Surveillance & Anomaly Detection System

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://reactjs.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-ResNet50-EE4C2C.svg)](https://pytorch.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An enterprise-grade, human-in-the-loop vehicle undercarriage surveillance platform. Combines computer vision (ResNet50 transfer learning), real-time WebSocket stream ingestion, automatic license plate recognition (ALPR), spatial anomaly heatmapping, and active dataset fine-tuning.

---

## 🌟 Key Capabilities

### 🛡️ Guard Control Station
* **Real-Time Image Ingestion**: Instant streaming of undercarriage captures via WebSocket hub (`ws://localhost:8000/ws/guard`).
* **✨ AI Image Enhancer**: Adaptive contrast sharpening, night-vision brightness boost, and high-frequency edge filters (`contrast(1.4) brightness(1.15) saturate(1.25)`).
* **🚨 AI Spatial Anomaly Hotspot Overlay**: Bounding box visualization (`[28% x 32%]`) flagging foreign wiring or unapproved attachments.
* **🧠 Component Diagnostic Metrics**:
  * 🛡️ Chassis Structural Integrity Score
  * ⚡ Foreign Wire & Object Cleanliness
  * 💧 Fluid Leak & Stain Clearance
* **🔀 Side-by-Side Baseline Diff Viewer**: Automatic retrieval of a vehicle's previous undercarriage scan by license plate (`KA-01-MJ-4892`) to spot physical alterations.
* **🚨 Critical Threat Escalation Alarm**: Pulsing red alert banner and visual escalation when AI confidence exceeds 85% suspicious payload.
* **📥 Security Audit CSV & ZIP Exporter**: Downloadable timestamped audit log and 1-click dataset `.zip` archive generator.

### 🔬 Creator Command Center
* **📊 System Telemetry**: Live metric counters (Total Scans, Approved vs Rejected ratio, Model Accuracy %, Active Version).
* **🔬 AI Testing Sandbox**: Drag-and-drop or copy-paste any test image to evaluate the active model and immediately save it to `/approved` or `/rejected` training datasets.
* **📁 Dataset Gallery**: Browse every image saved in the fine-tuning dataset with status filters and 1-click ZIP export.
* **🧠 ResNet50 Model Lifecycle**: Model versioning, active model hot-swapping, and scheduled training pipelines.
* **👥 User & Access Control**: Manage Guard & Creator access credentials.

---

## 🏗️ System Architecture

```text
┌────────────────────────────────────────────────────────┐
│               Raspberry Pi / Edge Bot                   │
│   (Camera Capture + Preprocessing + WS Transmitter)    │
└───────────────────────────┬────────────────────────────┘
                            │ WebSocket JPEG Stream
                            ▼
┌────────────────────────────────────────────────────────┐
│                   FastAPI Backend                      │
│ ┌───────────────────┐  ┌─────────────────────────────┐ │
│ │  ResNet50 PyTorch │  │ ALPR & History Tracker      │ │
│ └───────────────────┘  └─────────────────────────────┘ │
│ ┌───────────────────┐  ┌─────────────────────────────┐ │
│ │ SQLite / AsyncORM │  │ Dataset & ZIP Export Engine │ │
│ └───────────────────┘  └─────────────────────────────┘ │
└───────────────────────────┬────────────────────────────┘
                            │ REST / WebSocket
                            ▼
┌────────────────────────────────────────────────────────┐
│               React + Vite Frontend UI                 │
│ ┌───────────────────┐  ┌─────────────────────────────┐ │
│ │ Guard Station     │  │ Creator Command Center      │ │
│ └───────────────────┘  └─────────────────────────────┘ │
└────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start (Local Development)

### Prerequisites
* **Python 3.10+**
* **Node.js 18+**

### 1. Backend Setup
```bash
cd backend
python -m venv venv

# Windows PowerShell:
.\venv\Scripts\Activate.ps1

# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Backend API will run at **`http://localhost:8000`** (Swagger docs at `http://localhost:8000/docs`).

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Frontend UI will run at **`http://localhost:5173`**.

---

## 🐳 Docker Deployment

Run the full stack with Docker Compose:

```bash
docker-compose up --build
```
* **Frontend**: `http://localhost:80`
* **Backend API**: `http://localhost:8000`

---

## 📤 How to Push to GitHub

Follow these steps to host this project on your GitHub account:

### 1. Initialize Git Repository (if not already done)
```bash
git init
git add .
git commit -m "Initial commit: Vehicle Undercarriage Surveillance System with AI Anomaly Detection"
```

### 2. Create a Repository on GitHub
1. Go to [github.com/new](https://github.com/new).
2. Repository name: `under-chassis-surveillance`.
3. Keep it **Public** or **Private**, then click **Create repository**.

### 3. Link Remote & Push Code
```bash
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/under-chassis-surveillance.git
git branch -M main
git push -u origin main
```

---

## 🔑 Default Credentials

| Role | Username | Password |
|---|---|---|
| **Security Guard** | `guard` | `guard123` |
| **System Creator** | `creator` | `creator123` |

---

## 📄 License
Distributed under the **MIT License**. See `LICENSE` for details.
