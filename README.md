# 🌾 TurSathi AI (तूरसाथी AI)

> **Empowering Pigeon Pea (Tur / Arhar) Farmers with AI-Driven Disease Diagnosis, Voice Assistance & Smart Spray Guidance.**

TurSathi AI is a specialized agricultural mobile and cloud application designed specifically for **Pigeon Pea (तूर / अरहर / *Cajanus cajan*)** farmers across India. It provides real-time leaf disease detection, multilingual voice assistance (Marathi, Hindi, English), safety-gated image validation, and dynamic per-pump spray recommendations.

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [End-to-End Workflow Flowchart](#-end-to-end-workflow-flowchart)
- [System Architecture](#-system-architecture)
- [Deep Learning & ML Pipeline](#-deep-learning--ml-pipeline)
- [Tech Stack](#-tech-stack)
- [Repository Structure](#-repository-structure)
- [Installation & Setup](#-installation--setup)
  - [Prerequisites](#prerequisites)
  - [1. Backend Setup (FastAPI)](#1-backend-setup-fastapi)
  - [2. Mobile App Setup (React Native / Expo)](#2-mobile-app-setup-react-native--expo)
- [API Endpoints Overview](#-api-endpoints-overview)
- [Localization (i18n)](#-localization-i18n)
- [Security & Quality Assurance](#-security--quality-assurance)
- [Contributing & License](#-contributing--license)

---

## 🌟 Overview

Pigeon Pea (Tur) is a vital pulse crop in India, frequently threatened by destructive diseases such as **Fusarium Wilt**, **Sterility Mosaic Disease (SMD)**, and **Phytophthora Blight**. Early diagnosis and precise spray guidance prevent severe crop loss. 

**TurSathi AI** bridges the gap between agricultural science and field farmers by providing an accessible, voice-first mobile app that runs offline-resilient AI diagnostics and step-by-step verified chemical and organic treatment advisories.

---

## 🚀 Key Features

1. **🌿 Real-Time Tur Leaf Diagnosis**:
   - High-accuracy disease prediction from leaf photos using transfer-learned **EfficientNet-B0** convolutional neural networks.
   - Recognizes Fusarium Wilt, Phytophthora Blight, Sterility Mosaic Disease (SMD), Cercospora Leaf Spot, and Healthy leaves.

2. **🛡️ 2-Tier Tur Image Validator Gate (V3)**:
   - Dedicated gate model that validates whether a captured image is genuinely a Tur leaf before processing disease prediction.
   - Filters out non-crop images, weeds, human hands, and blurry inputs with high precision.

3. **🎙️ Multilingual Voice Problem Description**:
   - Farmers can speak and record their crop symptoms in their regional language (**Marathi**, **Hindi**, or **English**).
   - Voice reports are saved and linked directly to individual scan records.

4. **💧 Smart Spray Guidance (`/spray-guidance`)**:
   - Dynamic calculations for **15-Litre spray pumps** (quantity per pump, water ratio, timing, and mixing precautions).
   - Audio narration (Text-to-Speech) to read spray instructions aloud in Marathi, Hindi, or English.

5. **📋 Treatment Recommendation & Prescription (`/prescription`)**:
   - Complete breakdown of active ingredients, recommended commercial brands, dosage per hectare/acre, and farmer safety measures.

6. **🔒 Multi-Auth Support**:
   - JWT-based token authentication with support for standard email/password registration and Google OAuth sign-in.

---

## 🔄 End-to-End Workflow Flowchart

```text
[ Farmer Captures Leaf Photo ]
              │
              ▼
[ Tur Image Validator Gate (V3) ]
       │                │
(Valid Tur Leaf)   (Invalid / Non-Tur Image)
       │                │
       │                └───► [ Prompt: Retake Leaf Photo in Daylight ]
       ▼
[ Problem Description Page ]
       │
   (Record Voice Message in Marathi / Hindi / English)
       │
       ▼
[ Disease Prediction & Voice Upload ]
       │
       ▼
[ Smart Spray Guidance Screen ]
       │ ───► 15L Pump Calculation & Voice Playback
       │
       ▼ (Taps "More Information / अधिक माहिती / अधिक जानकारी")
[ Treatment Recommendation Screen (/prescription) ]
       │ ───► Chemical dosage, active ingredients & precautions
       │
       ▼
[ "Scan Another Leaf" (Reset Session) ]
```

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 TurSathi AI Mobile Client                   │
│         (React Native 0.86 • Expo SDK 57 • TypeScript)      │
│  - Multilingual UI (English, मराठी, हिंदी)                 │
│  - Expo Audio Recording & Expo Speech TTS                   │
│  - Responsive & Safe Screen Navigation (Expo Router)        │
└──────────────┬───────────────────────────────▲──────────────┘
               │ HTTP REST Requests (JWT Auth) │ JSON Responses
               ▼                               │
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend Server                    │
│            (Python 3.10+ • Uvicorn • SQLAlchemy)            │
│  - Authentication & OAuth Token Validation                  │
│  - Upload & Scan Management                                 │
│  - Agricultural Knowledge Engine                            │
└──────────────┬───────────────────────────────▲──────────────┘
               │ PyTorch Tensors               │ Predictions
               ▼                               │
┌─────────────────────────────────────────────────────────────┐
│                  Machine Learning Engine                    │
│  - Tur Image Validator V3 (EfficientNet-B0 Gate)            │
│  - Tur Disease Classifier (EfficientNet-B0 Deep CNN)        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧠 Deep Learning & ML Pipeline

| Model Stage | Architecture | Target Classes | Optimization / Backbone |
| :--- | :--- | :--- | :--- |
| **Tur Image Validator (Gate)** | EfficientNet-B0 | `tur_leaf` vs `non_tur` | Custom Head, Binary Cross-Entropy, Real-world Hard Negatives |
| **Disease Predictor** | EfficientNet-B0 | • Fusarium Wilt<br>• Phytophthora Blight<br>• Sterility Mosaic (SMD)<br>• Cercospora Leaf Spot<br>• Healthy Leaf | Multi-class Softmax, Transfer-learning on augmentated pulse crop dataset |

---

## 💻 Tech Stack

### Mobile Frontend
- **Framework**: React Native with Expo (SDK 57)
- **Language**: TypeScript
- **Navigation**: Expo Router (File-based routing)
- **Audio & Speech**: `expo-audio`, `expo-speech`
- **Design System**: Custom agricultural palette (`#1A4D33` Forest Green, `#F8F6F0` Cream, `#C7A45A` Gold)

### Backend API
- **Framework**: FastAPI (Python)
- **Server**: Uvicorn ASGI
- **Database**: SQLite (Development) / PostgreSQL (Production) with SQLAlchemy ORM & Alembic migrations
- **Authentication**: OAuth2 with JWT (JSON Web Tokens) & Google Auth

### Machine Learning & Data
- **Engine**: PyTorch & torchvision
- **Data Augmentation**: Albumentations / torchvision transforms
- **Model Formats**: Torchscript / `.pth` state dicts

---

## 📁 Repository Structure

```
TurSathi-AI/
├── backend/                  # FastAPI backend server
│   ├── alembic/              # Database migrations
│   ├── app/
│   │   ├── api/v1/           # API routes (auth, scans, predictions, recommendations)
│   │   ├── core/             # Configuration & security settings
│   │   ├── database/         # SQLAlchemy models and session engine
│   │   ├── ml/               # Image gate validator & disease predictor modules
│   │   ├── schemas/          # Pydantic data schemas
│   │   └── services/         # Business logic services
│   ├── tests/                # Automated backend test suites
│   ├── main.py               # Server entry point
│   └── requirements.txt      # Python dependencies
│
├── mobile/                   # React Native (Expo) mobile application
│   ├── assets/               # Icons, images, and splash graphics
│   ├── src/
│   │   ├── app/              # Expo Router screen pages
│   │   │   ├── index.tsx                 # Splash / Gateway screen
│   │   │   ├── language-selection.tsx    # Language selector (EN / MR / HI)
│   │   │   ├── login.tsx                 # Authentication screen
│   │   │   ├── register.tsx              # Account creation screen
│   │   │   ├── scan.tsx                  # Camera capture & image validation
│   │   │   ├── problem-description.tsx   # Voice recording & submission
│   │   │   ├── spray-guidance.tsx        # Smart spray pump calculations
│   │   │   └── prescription.tsx          # Comprehensive treatment prescription
│   │   ├── components/       # Reusable UI widgets and icons
│   │   ├── config/           # API routes & client configurations
│   │   ├── contexts/         # React Contexts (Language, Auth)
│   │   └── i18n/             # Multilingual translations dictionary
│   ├── package.json          # Node dependencies & Expo config
│   └── tsconfig.json         # TypeScript configuration
│
├── ml/                       # Machine learning training scripts
│   └── training/             # Scripts for validator & disease model training
├── models/                   # Saved PyTorch model checkpoints (.pth)
├── datasets/                 # Training and holdout dataset assets
├── reports/                  # Validation reports, test results, and audits
└── README.md                 # Project documentation
```

---

## ⚙️ Installation & Setup

### Prerequisites
- **Python**: 3.10 or higher
- **Node.js**: v18 or higher & `npm`
- **Expo Go App**: (Optional for physical device testing) or Android Emulator / iOS Simulator

---

### 1. Backend Setup (FastAPI)

1. Open a terminal and navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the database migrations (Alembic):
   ```bash
   alembic upgrade head
   ```

5. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   *The Swagger API documentation will be available at:* `http://localhost:8000/docs`

---

### 2. Mobile App Setup (React Native / Expo)

1. Open a second terminal and navigate to the mobile directory:
   ```bash
   cd mobile
   ```

2. Install Node.js dependencies:
   ```bash
   npm install
   ```

3. Configure your API base URL in `mobile/src/config/api.ts` to match your local IP address:
   ```typescript
   export const API_BASE_URL = 'http://<YOUR_LOCAL_IP>:8000';
   ```

4. Launch the Expo development server:
   ```bash
   npx expo start --clear
   ```

5. Press `a` for Android Emulator, `i` for iOS Simulator, or scan the QR code with **Expo Go** on your phone.

---

## 📡 API Endpoints Overview

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/auth/register` | Register a new farmer account |
| `POST` | `/api/v1/auth/login` | Login and receive JWT access token |
| `POST` | `/api/v1/auth/google` | Sign in / Authenticate with Google ID Token |
| `POST` | `/api/v1/scans/upload` | Upload leaf image & run Tur leaf validation gate |
| `POST` | `/api/v1/scans/{id}/voice` | Upload farmer voice symptom description |
| `POST` | `/api/v1/predictions/predict/{id}` | Run disease classifier on validated scan |
| `GET`  | `/api/v1/recommendations/tur/{disease}/spray-guidance` | Fetch dynamic 15L pump spray calculations |

---

## 🌐 Localization (i18n)

TurSathi AI provides native localization for Indian agriculture:

| Language | Code | Region | Support Level |
| :--- | :---: | :--- | :--- |
| **English** | `en` | Pan-India / Research | Full UI, Audio TTS, Medical Prescriptions |
| **मराठी (Marathi)** | `mr` | Maharashtra / Vidarbha / Marathwada | Full UI, Audio TTS, Native Farming Terms |
| **हिंदी (Hindi)** | `hi` | Northern & Central India | Full UI, Audio TTS, Hindi Agronomy Lexicon |

---

## 🔒 Security & Quality Assurance

- **Zero Non-Tur Inference Waste**: Invalid images are stopped at the first gate to save cloud compute and avoid false prescriptions.
- **Farmer Data Privacy**: Uploaded voice reports and photos are securely referenced per farmer ID.
- **Safety Overrides**: AI confidence below 60% automatically warns the user to retake the photo in daylight before applying chemicals.

---

## 👨‍🌾 Contributing & License

Contributions, bug reports, and dataset augmentations are welcome.

Developed with ❤️ for Indian farmers.  
**TurSathi AI** — *तुमचा विश्वासू कृषी मित्र.*
