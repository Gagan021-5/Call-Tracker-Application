# 📱 Call Tracer App

A full-stack call-log tracking and analytics application designed for sales team monitoring with disclosed and consensual employee monitoring on company-issued Android devices.

---

## 🏗️ Tech Stack

- **Mobile (Frontend):** React Native (Expo SDK 54, React 19)
  - **Typography:** Clash Display (Display / KPI) & Inter (Body UI)
  - **Charts:** `react-native-chart-kit` (Volume trends & duration breakdown)
  - **State & Storage:** `expo-secure-store` (JWT tokens) & `@react-native-async-storage/async-storage`
  - **Call Log Reader:** `react-native-call-log`
  - **Background Tasks:** `expo-background-task` + `expo-task-manager`
- **Backend:** Django 5 + Django REST Framework + PostgreSQL
  - **Authentication:** JWT (`djangorestframework-simplejwt`)
  - **Database:** PostgreSQL (`psycopg3`)
  - **Aggregation Engine:** Custom Django management commands for daily analytics

---

## 📂 Project Structure

```
Call Tracer App/
├── backend/                  # Django REST API & PostgreSQL backend
│   ├── api/                  # Models (User, CallLog, CallStats), Views, Serializers
│   ├── calltracer/           # Project settings & URL configuration
│   ├── .env.example          # Environment variable template
│   ├── manage.py
│   └── requirements.txt
├── callapp/                  # React Native / Expo mobile application
│   ├── app/                  # Expo Router file-based navigation
│   │   ├── (auth)/           # Login & Registration screens
│   │   ├── (user)/           # Consent Disclosure & Sync Status screens
│   │   └── (admin)/          # Team Dashboard, Call Logs table, Analytics charts
│   ├── assets/               # Fonts (Clash Display) & Icons
│   ├── constants/            # Design tokens & Typography
│   ├── services/             # Axios API client & background sync worker
│   └── package.json
├── .gitignore                # Root gitignore (secrets, node_modules, build artifacts)
└── README.md
```

---

## 🚀 Quick Start Guide

### 1. Backend Setup

```bash
cd backend

# Copy environment variables
cp .env.example .env

# Install Python dependencies
pip install -r requirements.txt

# Run database migrations
python manage.py migrate

# (Optional) Seed realistic dummy data for testing
python manage.py seed_dummy_data

# Start the development server (accessible over LAN)
python manage.py runserver 0.0.0.0:8000
```

### 2. Frontend Setup

```bash
cd callapp

# Install Node dependencies
npm install

# Start Expo with clean cache
npx expo start -c
```

---

## 🔒 Security & Privacy Notice
This application is intended strictly for company-issued devices with explicit employee disclosure and consent. No call audio recordings are captured; only call metadata (number, duration, direction, timestamp) is synced for analytics.
