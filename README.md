# Call Tracer App

A full-stack call-log tracking and analytics application designed for sales team monitoring with disclosed and consensual employee monitoring on company-issued Android devices.

---

## Tech Stack

- **Mobile (Frontend):** React Native (Expo SDK 54, React 19)
  - **Typography:** Clash Display (Display / KPI) & Inter (Body UI)
  - **Charts:** `react-native-chart-kit` (Volume trends & duration breakdown)
  - **State & Storage:** `expo-secure-store` (JWT tokens) & `@react-native-async-storage/async-storage`
  - **Call Log Reader:** `react-native-call-log`
  - **Background Tasks:** `expo-background-task` + `expo-task-manager`
  - **Network Security:** Custom Expo config plugin for local HTTP/cleartext traffic
- **Backend:** Django 5 + Django REST Framework + PostgreSQL
  - **Authentication:** JWT (`djangorestframework-simplejwt`)
  - **Database:** PostgreSQL (`psycopg3`)
  - **Aggregation Engine:** Real-time query aggregation with `TruncDate` & Django management commands

---

## Key Features

1. **Multi-Tenant Company Connect Codes:**
   - Unique connect codes (`XXX-NNNN-NNNN`) for manager isolation.
   - Native OS share sheet integration (WhatsApp, Slack, Gmail, Messages).
   - Strict admin-scoped employee and log filtering.

2. **Native Telephony Synchronization:**
   - Automated synchronization of incoming, outgoing, and missed call logs.
   - Safe TurboModule resolution and background syncing.
   - Zero-flicker employee status screen.

3. **Admin Dashboard & Team Management:**
   - Live team members list with call volume counts and formatted last call timestamps.
   - In-app Admin Account Settings modal for updating admin credentials and passwords directly in PostgreSQL.

4. **Real-Time Analytics & Live Performance Graphs:**
   - 7-day live call volume curve with bezier rendering.
   - Interactive employee carousel filter (team-wide vs individual employee).
   - Categorized distribution (Incoming, Outgoing, Missed) and ranked top client phone numbers.

5. **Interactive Calendar Date Picker & Call Logs:**
   - Full month grid date-range selector with quick presets (Today, Yesterday, Last 7D, This Month, All Time).
   - Filter by call direction, search by phone number or employee name.

---

## Project Structure

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
│   ├── assets/               # Fonts (Clash Display) & Logo assets
│   ├── constants/            # Design tokens & Typography
│   ├── contexts/             # AuthContext & JWT state management
│   ├── plugins/              # withNetworkSecurityConfig plugin for EAS builds
│   ├── services/             # Axios API client & background sync worker
│   ├── app.json              # Expo application configuration
│   └── eas.json              # EAS Build configuration
├── .gitignore                # Root gitignore (secrets, node_modules, build artifacts)
└── README.md
```

---

## Quick Start Guide

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

### 3. Standalone Android APK Build (EAS)

```bash
cd callapp

# Build standalone Android APK
npx eas-cli build -p android --profile preview
```

---

## Security & Privacy Notice

This application is intended strictly for company-issued devices with explicit employee disclosure and consent. No call audio recordings are captured; only call metadata (number, duration, direction) is tracked.
