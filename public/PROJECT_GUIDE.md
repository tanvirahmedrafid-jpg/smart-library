# Smart Library Management System (SLMS)
### Intelligent Library Management with Rule-Based Book Demand Analytics & Security Control
**S-liBro: Your Smart Campus Library System**

---

## 🎨 Theme: High-Tech Orange & Blue
- **Midnight & Royal Blue (`#0F172A`, `#1E3A8A`)**: Top navigation, structural cards, audit logs, and data tables.
- **Electric Smart Orange (`#FF6B00`, `#EA580C`)**: Dynamic CTA buttons, demand badges, shortage alerts, and AI indicators.
- **Ice Slate Canvas (`#F8FAFC`, `#FFFFFF`)**: Glassmorphism cards with responsive layouts.

---

## 🚀 How to Run the Project

### Option 1: One-Click Startup (Windows)
Double-click the **`run_server.bat`** file in the project folder.

### Option 2: Terminal / PowerShell
```powershell
.\.venv\Scripts\python.exe manage.py runserver
```
Then open your web browser:
👉 **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)**

---

## 👥 Distinct User Portals & Strict Access Control

Each role has a **dedicated, restricted portal** protected by server-side authentication and role-checking decorators. Unauthenticated users cannot access any dashboard without logging in first.

| Role | Username | Password | Dedicated Workspace | Security & Permissions |
| :--- | :--- | :--- | :--- | :--- |
| **Student** | `tanvir` | `stu123` | **Student Portal** (`/my-library/`) | Active loans, due dates, fines, AI recommendations, **Resource Demand Survey**. Blocked from staff & admin desks. |
| **Student** | `rahim` | `stu123` | **Student Portal** (`/my-library/`) | Active loans, student services. |
| **Librarian** | `librarian` | `lib123` | **Librarian Desk** (`/staff-desk/`) | **Rule-Based Book Demand Analytics**, Stock Shortage Alerts, Issue/Return desk, Member management, Reports. Blocked from admin portal. |
| **Administrator** | `admin` | `admin123` | **Admin Security Control** (`/admin-portal/`) | **Password Reset Management**, **Live Database Backup Download**, **Security Audit Trail**, Policy & Weight configuration, Django Admin (`/admin/`). |

---

## 📊 1. Rule-Based Book Demand Analytics (Librarian Desk)
Located directly on the **Librarian Workspace (`/staff-desk/`)**, this module computes a composite demand score $D$ for every book in the collection using the explainable formula:

$$D = (w_B \times B_{\text{norm}}) + (w_R \times R_{\text{norm}}) + (w_S \times S_{\text{norm}}) + (w_Q \times Q_{\text{norm}})$$

* **$B$ (Borrowing Activity, 40%)**: Normalized historical loan count.
* **$R$ (Reservation Activity, 25%)**: Normalized waiting list queue.
* **$S$ (Survey Interest, 20%)**: Stated student preference votes collected via the Student Portal Survey.
* **$Q$ (Catalog Searches, 15%)**: Normalized search frequencies recorded in the catalog.

### ⚠️ Automated Stock Shortage Alerts
When a title's Demand Score $D \ge 50$ (or configured threshold) and available physical copies on shelf $\le 1$, the system automatically triggers an **Acquisition Alert** for the librarian with supporting evidence (waiting list length, demand score, copies available), helping staff make evidence-based book acquisition decisions.

---

## 🛡️ 2. Administrator Security, Password & Database Features
Located on the **Administrator Control Center (`/admin-portal/`)**:

1. **User Password Management & Reset**:
   - Admin can select any account (student, librarian, staff) and securely set a new password directly from the portal with confirmation checks and validation.
2. **Database Maintenance & One-Click Backup**:
   - Inspect live SQLite database metrics (file size in KB, engine status, last written timestamp, total table counts).
   - Click **"Download Database Backup"** to get an instant, downloadable `.sqlite3` backup file.
3. **Security Audit Trail (`SecurityAuditLog`)**:
   - Tracks all system security events:
     - Successful Logins & Failed Login attempts (with IP addresses)
     - User Logouts
     - Password Resets performed by Admin
     - Role Changes & Account Status Modifications
     - Database Backup downloads
4. **Circulation & Formula Configuration**:
   - Live settings form to update loan duration, maximum active loans, daily overdue fine, and demand scoring weights ($w_B, w_R, w_S, w_Q$).

---

## 🤖 3. Smart & AI Features
- **Google Gemini AI Assistant (`library/services/gemini.py`)**:
  - Connects to Google AI Studio's free tier (`gemini-2.5-flash` or `gemini-1.5-flash`).
  - Reads keys securely from `.env` via `GEMINI_API_KEY` and `GEMINI_MODEL`.
  - Strictly grounded in the Django SQLite database (`Book` catalog) to eliminate hallucinations.
  - Automatically falls back to local database search if the key is missing or quota is reached.
- **LibroAI Assistant**: Floating interactive chatbot answering queries on book availability, categories, and library fine policies.
- **Predictive Live Search**: Instant AJAX search dropdown showing real-time shelf copy availability.
- **AI-Assisted Recommendations**: Recommends personalized titles based on member borrowing history and department interests.
- **Student Resource Demand Survey**: Collects student feedback on needed books and unavailable topics on the Student Dashboard.

---

## 🖼️ 4. Image Asset Organization
Assets are structured under `static/library/images/`:
- `brand/`:
  - `logo.png` — High-resolution transparent PNG logo.
  - `open_book_icon.png` — App icon and Apple touch icon.
  - `favicon.ico` — Multi-resolution browser favicon.
- `promotions/`:
  - `smart_campus_banner.png` (and `.webp`) — Homepage hero banner.
  - `smart_campus_poster.png` (and `.webp`) — Academic support poster.
  - `smart_campus_launch.png` (and `.webp`) — Digital platform announcement graphic.
- `books/`:
  - `cover_algorithms.jpg`, `cover_database.jpg`, `cover_literature.jpg`, `cover_physics.jpg` (with WebP alternates) formatted with 3D perspective and uniform padding.

---

## 🚪 5. Robust Logout System
- **Desktop Navigation**: Prominent red/coral `🚪 Log out` button in the header next to the user chip on every page.
- **Mobile Drawer Navigation**: Dedicated logout option inside the mobile hamburger menu.
- **Direct Portal Headers**: One-click `🚪 Log out` action inside Student Portal (`/my-library/`), Librarian Desk (`/staff-desk/`), and Admin Portal (`/admin-portal/`).
- **Security & Session Termination**: Supports both GET and POST requests, flushes user session data, records a `LOGOUT` event in `SecurityAuditLog`, and redirects to `/login/` with a friendly confirmation flash alert.

