# DEALCALL — COMPLETE SYSTEM DOCUMENTATION & WORKFLOW
---

## 1. Executive Summary
**DealCall** is an enterprise sales call monitoring, telephony synchronization, and real-time performance analytics platform. It enables sales managers and business leaders to track registered sales representatives' call activities across company Android devices through background telephony synchronization, dedicated manager dashboards, 3-card Bento metrics, real-time volume curves, and interactive calendar filtering.

---

## 2. System Architecture & Technology Stack

### A. Mobile Application (Frontend Client)
* **Framework:** React Native with Expo (SDK 54, React 19, TypeScript)
* **Design System:** **Nexus Pro Aesthetics** (Royal Indigo `#5454D4`, Soft Periwinkle `#877CFF`, Sky Blue `#4E95FF`, Aqua Teal `#00C2CB`, and Airy Light Canvas `#F4F6FB`)
* **Routing:** Expo Router (File-based navigation with direct role gating)
* **Typography:** Clash Display (Bento KPIs & Section Titles) & Inter (Body UI, Inputs, Labels)
* **State & Secure Storage:** `expo-secure-store` (Hardware-backed encrypted keychain for JWT tokens)
* **Telephony Module:** `react-native-call-log` (Android native telephony content resolver)
* **Background Worker:** `expo-background-task` + `expo-task-manager` + App State foreground listeners (30-second interval sync)
* **Data Visualization:** `react-native-chart-kit` (Live bezier call volume curves & category breakdown)

### B. Backend API & Processing Engine
* **Framework:** Django 5.0 + Django REST Framework (DRF)
* **Authentication:** JSON Web Tokens (`djangorestframework-simplejwt`) with Token Refresh
* **Deduplication Engine:** High-performance `bulk_create(ignore_conflicts=True)` with composite unique indexes
* **Real-Time Aggregator:** Django ORM `TruncDate`, `Count`, `Sum`, and `Max` live SQL grouping
* **Production Web Server:** Gunicorn WSGI + WhiteNoise static asset engine

### C. Database Layer
* **RDBMS:** PostgreSQL (`psycopg3` driver)
* **Role Separation:** Platform-wide role-based access (`role='admin'` vs `role='user'`)

---

## 3. Core Roles & System Model

```
                          ┌──────────────────────────┐
                          │   Company Admin/Manager  │
                          │   (DealCall Analytics)   │
                          └────────────┬─────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    ▼                                     ▼
        ┌───────────────────────┐             ┌───────────────────────┐
        │  Sales Employee 1     │             │  Sales Employee 2     │
        │  (Device: Galaxy S24) │             │  (Device: Pixel 8)    │
        └───────────────────────┘             └───────────────────────┘
```

1. **Company Admin / Manager (`role = 'admin'`):**
   * Access to the **DealCall Team Dashboard**, viewing all registered employees, live sync health, and total call volumes.
   * Access to **Performance Hub** with 7-day volume curves, call distribution arcs (Incoming, Outgoing, Missed), and top client numbers.
   * Access to **Call Activity Logs** with Google-style month/year calendar navigator and quick date presets.
   * In-app **Admin Settings Modal** to update credentials and passwords directly in PostgreSQL.

2. **Sales Employee (`role = 'user'`):**
   * Direct registration with **Username**, **Work Email**, and **Password**.
   * One-time Android telephony permission grant (`READ_CALL_LOG` + `READ_PHONE_STATE`).
   * Runs quiet 30-second background syncs with zero screen flickering.
   * Syncs incoming, outgoing, and missed call metadata to PostgreSQL.

---

## 4. End-to-End Workflow & Step-by-Step Data Flow

### Step 1: Direct Employee Registration & Auto-Login
1. An employee installs the app and opens the **Register** screen.
2. The employee enters their **Username**, **Work Email**, and **Password** (min 8 chars).
3. The Django backend creates the account with `role='user'` and returns a JWT token pair.
4. The app redirects the employee directly to their **Status Screen** (`/(user)/status`).

### Step 2: Native Telephony Access & Background Sync
1. On the employee device, the app checks Android runtime permissions:
   * `android.permission.READ_CALL_LOG`
   * `android.permission.READ_PHONE_STATE`
2. Once granted, the employee screen displays a permanent **`DEALCALL SYNC ACTIVE`** pulse badge.
3. The client sync engine queries Android’s native telephony content provider (`CallLog.Calls`) whenever:
   * The employee opens or returns to the app (App Foreground resume).
   * The employee pulls down to refresh.
   * The 30-second periodic background interval worker triggers.
4. Call metadata is gathered:
   * **Phone Number:** e.g., `+919876543210`
   * **Call Type:** `incoming`, `outgoing`, or `missed`
   * **Duration:** Call length in seconds
   * **Timestamp:** Exact ISO 8601 UTC timestamp

### Step 3: Backend Ingestion & Deduplication
1. The mobile client sends a JSON payload to `POST /api/call-logs/sync/`:
   ```json
   {
     "call_logs": [
       {
         "phone_number": "+919876543210",
         "call_type": "outgoing",
         "duration": 145,
         "timestamp": "2026-09-01T09:30:00Z"
       }
     ]
   }
   ```
2. The Django backend parses the batch, associates logs with the employee, and executes:
   ```python
   CallLog.objects.bulk_create(instances, ignore_conflicts=True)
   ```
3. **Deduplication Guarantee:** The database contains a unique composite constraint on `(user_id, phone_number, timestamp)`. If a call was already synced, PostgreSQL skips it without error.

### Step 4: PostgreSQL Database Schema
* **`users` Table:** Stores user IDs, hashed passwords, roles (`admin` / `user`), and device IDs.
* **`api_calllog` Table:** Stores individual call records indexed by `user_id`, `timestamp`, `phone_number`, and `call_type`.

### Step 5: Admin Dashboard & Real-Time Analytics
When the admin opens the dashboard:
1. **DealCall Bento KPI Carousel (`GET /api/admin/users/`):**
   * **Team Members:** Live member count with `+12.4%` growth badge.
   * **Total Call Records:** Aggregated call volume with `+8.5%` trend badge.
   * **Sync Health:** Real-time pulse indicator (`99.4% Live`).
2. **Persistent Search Capsule:**
   * Pure white elevated search card with `⌘ F` shortcut, allowing fluid search without keyboard dismissal.
3. **Team Performance Hub (`GET /api/admin/stats/`):**
   * Groups records live by date using `TruncDate("timestamp")`.
   * Renders a 7-day live call volume curve, call distribution percentages (Incoming/Outgoing/Missed), and top 5 contacted phone numbers.
   * Interactive **Member Carousel** allowing one-tap switching between "All Team" and individual sales reps.
4. **Interactive Calendar Call Logs (`GET /api/admin/call-logs/`):**
   * Visual month/year calendar navigator with quick presets: `Today`, `Yesterday`, `Last 7D`, `This Month`, and `All Time`.

### Step 6: In-App Admin Credential Management
* Tapping the **`🔑` Key Icon** on the Team Dashboard opens the **Admin Settings Modal**.
* The manager can change their username, work email, and password.
* When saved, `PATCH /api/admin/profile/` updates the PostgreSQL database securely using PBKDF2 hashing.

---

## 5. Complete REST API Specification

| Endpoint | Method | Role | Description | Request / Query Parameters | Response |
| :--- | :---: | :---: | :--- | :--- | :--- |
| `/api/auth/register/` | `POST` | Public | Direct employee registration | `username`, `email`, `password`, `password_confirm` | `201 Created` + JWT Tokens |
| `/api/auth/login/` | `POST` | Public | Sign in | `username`, `password` | `200 OK` + Access/Refresh Tokens + Profile |
| `/api/auth/refresh/` | `POST` | Public | Refresh JWT access token | `refresh` | `200 OK` + New Access Token |
| `/api/call-logs/sync/` | `POST` | Employee | Sync call logs batch | Array of `{phone_number, call_type, duration, timestamp}` | `200 OK` + `{synced, skipped_duplicates}` |
| `/api/admin/profile/` | `GET` | Admin | Get admin profile | None | `200 OK` + `{username, total_employees}` |
| `/api/admin/profile/` | `PATCH` | Admin | Update credentials / password | `username`, `email`, optional `password` | `200 OK` + Updated Profile |
| `/api/admin/users/` | `GET` | Admin | List all registered employees | `search`, `page` | `200 OK` + Array of employees with call counts & `last_call_timestamp` |
| `/api/admin/call-logs/` | `GET` | Admin | View all team call records | `user_id`, `start_date`, `end_date`, `call_type`, `search`, `page` | `200 OK` + Paginated call records |
| `/api/admin/stats/` | `GET` | Admin | Team performance analytics | Optional `?user_id=` | `200 OK` + Daily trend array, breakdown, top numbers |

---

## 6. Mobile Application Screen Structure

```
callapp/
├── constants/
│   └── theme.ts               # Design tokens (Indigo, Periwinkle, Blue, Aqua, Shadows)
├── app/
│   ├── index.tsx              # Gatekeeper router (directs to admin dashboard or employee status)
│   ├── (auth)/
│   │   ├── login.tsx          # DealCall sign-in card with secure inputs
│   │   └── register.tsx       # Direct employee registration (Username, Email, Password)
│   ├── (user)/
│   │   └── status.tsx         # Zero-flicker employee device status & auto-sync screen
│   └── (admin)/
│       ├── _layout.tsx        # Floating dock tab navigator (Team, Call Logs, Analytics)
│       ├── users.tsx          # Team dashboard, 3-card Bento metrics, and Admin Settings modal
│       ├── call-logs.tsx      # Call activity records with interactive visual calendar date picker
│       └── stats.tsx          # Performance hub, member carousel, and 7-day live volume curve
```

---

## 7. Security, Privacy & Data Compliance

1. **No Audio Recording:** The application strictly avoids audio recording, interception, or voice upload. Only standard telephony metadata (number, direction, duration, timestamp) is synchronized.
2. **Hardware Keychain Encryption:** Authentication tokens are stored in the device's hardware-backed secure storage using `expo-secure-store`.
3. **Role-Based Access Control:** All administrative endpoints enforce `IsAdminRole` permissions before exposing aggregated employee call data.
4. **Network Security Config:** Configured with Android network security policy plugins to ensure secure transport across mobile networks and local test environments.
