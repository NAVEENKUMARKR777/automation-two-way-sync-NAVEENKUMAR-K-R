# Lead-Work Tracker Sync

A lightweight two-way synchronization system between Google Sheets (Lead Tracker) and a FastAPI work management service.

## 🎯 Overview

This project implements bidirectional sync between:

- **Lead Tracker** — Google Sheets spreadsheet for managing sales leads
- **Work Tracker** — FastAPI service with SQLite backend for task management

The sync layer handles real-time updates, maintains idempotency, and provides comprehensive logging with error handling.

## 🏗️ Architecture

<img width="764" height="113" alt="Screenshot 2025-12-04 134304" src="https://github.com/user-attachments/assets/206f7b4e-03ba-477d-a3dd-86ab86163a03" />


### Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Lead Tracker | Google Sheets | Store and manage leads |
| Work Tracker | FastAPI + SQLite | Task management backend |
| Sync Service | Python | Orchestrate two-way sync |

## 📊 Data Models

### Lead (Google Sheets)

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique lead identifier |
| `name` | string | Lead contact name |
| `email` | string | Contact email |
| `status` | enum | Current lead status |
| `source` | string | Lead source (optional) |
| `task_id` | string | Linked Work Tracker task ID |

**Lead Status Values:** `NEW` • `CONTACTED` • `QUALIFIED` • `LOST`

### Task (Work Tracker)

| Field | Type | Description |
|-------|------|-------------|
| `id` | string (UUID) | Unique task identifier |
| `title` | string | Task title |
| `status` | enum | Current task status |
| `lead_id` | string | Reference to Lead ID |
| `notes` | string | Additional notes (optional) |

**Task Status Values:** `TODO` • `IN_PROGRESS` • `DONE`

### Status Mapping

**Lead → Task**
- `NEW` → `TODO`
- `CONTACTED` → `IN_PROGRESS`
- `QUALIFIED` → `DONE`
- `LOST` → `DONE`

**Task → Lead**
- `TODO` → `NEW`
- `IN_PROGRESS` → `CONTACTED`
- `DONE` → `QUALIFIED` (unless lead is `LOST`)

> **Note:** Leads with `LOST` status are terminal and won't be updated by task changes.

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher
- Google account with Sheets access
- Google Cloud Project with Service Account

### 1. Create Google Sheet

1. Navigate to [Google Sheets](https://sheets.google.com)
2. Create a new blank spreadsheet
3. Rename it to **Lead Tracker**
4. Rename the first tab to **Leads**
5. Add header row with these exact column names:

   | A | B | C | D | E | F |
   |---|---|---|---|---|---|
   | id | name | email | status | source | task_id |

6. Add sample data (leave `task_id` blank initially):

   ```
   lead-1    Alice Example    alice@example.com    NEW    Website    
   ```

7. Copy the **Spreadsheet ID** from the URL (between `/d/` and `/edit`)

### 2. Google Cloud Setup

1. Create/select a project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the **Google Sheets API** for your project
3. Create a **Service Account**:
   - Navigate to **IAM & Admin → Service Accounts**
   - Click **Create Service Account**
   - Assign **Project → Editor** role
4. Generate JSON key:
   - Select your service account
   - Go to **Keys** tab
   - Click **Add Key → Create New Key → JSON**
   - Save as `service-account.json` in project root
5. Share your Google Sheet with the service account email
   - Grant **Editor** permissions

### 3. Environment Configuration

Create a `.env` file or set these environment variables:

```bash
GOOGLE_SERVICE_ACCOUNT_FILE=service-account.json
GOOGLE_SHEET_ID=your-spreadsheet-id-here
GOOGLE_SHEET_RANGE=Leads!A:F
WORK_TRACKER_BASE_URL=http://localhost:8000
DATABASE_URL=sqlite:///./worktracker.db
LOG_LEVEL=INFO
```

**PowerShell Example:**
```powershell
$env:GOOGLE_SERVICE_ACCOUNT_FILE="service-account.json"
$env:GOOGLE_SHEET_ID="your-spreadsheet-id"
$env:GOOGLE_SHEET_RANGE="Leads!A:F"
$env:WORK_TRACKER_BASE_URL="http://localhost:8000"
```

### 4. Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests (optional)
pytest
```

### 5. Start Work Tracker API

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

**Health check:**
```bash
curl http://localhost:8000/health
```

## 💻 Usage

### Initial Sync (Leads → Tasks)

Creates tasks for all leads that don't have a `task_id`:

```bash
python -m sync.sync --initial
```

This operation is **idempotent** — safe to run multiple times.

### Incremental Two-Way Sync

Syncs changes in both directions:

```bash
python -m sync.sync
```

**What happens:**
- **Leads → Tasks:** Updates task status based on lead changes
- **Tasks → Leads:** Updates lead status based on task changes (except `LOST` leads)

Schedule this command with cron or Task Scheduler for continuous sync.

## 🎬 Demo Walkthrough

### Step 1: Initial Setup
```bash
# Start the Work Tracker
uvicorn app.main:app --reload

# Run initial sync
python -m sync.sync --initial
```

Check your Google Sheet — the `task_id` column should now be populated.

### Step 2: Test Lead → Task Update

1. In Google Sheets, change a lead's status from `NEW` to `CONTACTED`
2. Run sync: `python -m sync.sync`
3. Verify at `http://localhost:8000/tasks` — task status should be `IN_PROGRESS`

### Step 3: Test Task → Lead Update

1. Identify the **canonical task** for a lead:
   - In Google Sheets, look at the lead's `task_id` column.
   - Use that value as `{task_id}` in API calls.
2. Update that task via API:
   ```bash
   curl -X PUT http://localhost:8000/tasks/{task_id} \
     -H "Content-Type: application/json" \
     -d '{"status": "DONE"}'
   ```
3. Run sync: `python -m sync.sync`
4. Check Google Sheets — that lead's `status` should be `QUALIFIED`

## 🛡️ Error Handling & Reliability

### Idempotency

- Each lead maintains a single **canonical** `task_id` reference
- Sync checks for existing `task_id` before creating new tasks
- Only the task whose `id` matches `task_id` is allowed to drive Task → Lead updates
- Safe to run sync multiple times without duplicates

### Error Management

- All HTTP errors are logged with method, URL, status code, and response body
- Network failures raise `TaskClientError` — caught to prevent full sync failure
- Google Sheets errors are logged per-record without stopping the entire sync
- Centralized logging configuration in `sync/sync.py`

## ⚠️ Limitations & Assumptions

- **Fixed Schema** — Google Sheets must have the exact header format specified
- **Polling-Based** — No webhook support; runs on-demand or via scheduler
- **Simple Conflict Resolution:**
  - `LOST` leads are terminal and never overwritten
  - `DONE` on the canonical task upgrades leads to `QUALIFIED`
  - No advanced concurrency control for simultaneous updates
- **Local Development** — No authentication implemented; designed for trusted environments

## 🤖 AI Usage Disclosure

### Tools Used
- **ChatGPT** (GPT-based assistant) in Cursor editor

### Assistance Provided
- Initial project structure scaffolding (FastAPI app, sync modules)
- Status mapping logic and sync flow suggestions
- Boilerplate code for Google Sheets API and HTTP clients

### Design Override
The AI suggested tracking a `last_synced_status` field to optimize updates. I chose a simpler approach: always map current status on each sync run, relying on `task_id` for idempotency and terminal state rules (`LOST` status). This reduces complexity while maintaining safety and transparency.

## 📹 Demo Video

*Coming soon — link will be added after recording*

Replace with: `https://drive.google.com/your-video-link` (set sharing to "Anyone with the link")

---

## 📝 Project Structure

```
.
├── app/
│   └── main.py              # FastAPI application
├── sync/
│   ├── sync.py              # Main sync script
│   ├── sync_logic.py        # Sync orchestration
│   ├── lead_client.py       # Google Sheets client
│   ├── task_client.py       # Work Tracker HTTP client
│   └── status_mapping.py    # Status conversion logic
├── requirements.txt
├── service-account.json     # (gitignored)
└── README.md
```

## 📄 License

*Add your license information here*

## 🤝 Contributing

*Add contribution guidelines here*
