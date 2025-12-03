## API Documentation

This document describes:

1. The JSON HTTP API exposed by the **Work Tracker** FastAPI service.
2. How the sync service interacts with the **Lead Tracker** (Google Sheets) via the Google Sheets API.

- **Base URL (local development)**: `http://localhost:8000`
- **Authentication**: None (local demo only)
- **Content-Type**: `application/json`
- **Task status enum**: `TODO`, `IN_PROGRESS`, `DONE`

You can exercise the Work Tracker endpoints with tools like **Postman**, **curl**, or your browser.  
Lead Tracker operations are performed via the `googleapiclient` Python SDK using a service account.

---

## Lead Tracker (Google Sheets)

### Sheet Structure

- The spreadsheet must contain a sheet/tab (default `Leads`) with the following columns:

  | Column | Header  | Description                               |
  |--------|---------|-------------------------------------------|
  | A      | `id`     | Unique lead identifier (string)           |
  | B      | `name`   | Lead contact name                         |
  | C      | `email`  | Contact email                             |
  | D      | `status` | One of `NEW`, `CONTACTED`, `QUALIFIED`, `LOST` |
  | E      | `source` | Optional source info                      |
  | F      | `task_id`| ID of the canonical Work Tracker task     |

### Access Pattern

- **Authentication**: Google Service Account JSON key shared with the sheet (Editor access).
- **Scopes**: `https://www.googleapis.com/auth/spreadsheets`
- **Read**: `spreadsheets.values.get` over the configured range (default `Leads!A:F`).
- **Write**: `spreadsheets.values.update` to modify specific rows (status, task_id, etc.).
- **Idempotency Anchor**: The `task_id` column records the UUID of the Work Tracker task linked to the lead. Only this canonical task can drive Task → Lead updates.
- **Terminal State**: Leads with status `LOST` are ignored by Task → Lead sync to avoid reactivating closed opportunities.

### Typical Lead → Task Flow

1. Sync reads all rows via `values.get`.
2. For each lead whose `status != LOST`:
   - If `task_id` is empty, create a task (see Work Tracker API) and write the new UUID back into `task_id`.
   - If `task_id` exists, update that task’s status to match the lead.

### Typical Task → Lead Flow

1. Sync fetches all leads (to know row numbers).
2. Fetch tasks from Work Tracker.
3. For each task:
   - Find the lead whose `task_id` equals the task’s `id`.
   - Map task status → lead status and call `values.update` on that row (unless the lead is `LOST`).

---

## Work Tracker API

### 1. Health Check

- **Method**: `GET`
- **URL**: `/health`

### Description

Simple endpoint to verify that the Work Tracker service is running.

### Request

- **Headers**: none required
- **Body**: _none_

### Responses

- **200 OK**

  ```json
  {
    "status": "ok"
  }
  ```

---

### 2. List All Tasks

- **Method**: `GET`
- **URL**: `/tasks`

### Description

Return all tasks currently stored in the Work Tracker database.

### Request

- **Headers**: none required
- **Body**: _none_

### Responses

- **200 OK**

  ```json
  [
    {
      "id": "4a4b4e1d-4f8b-4a3a-8ab8-0f8db21fcb1c",
      "title": "Follow up with Alice Example",
      "status": "TODO",
      "lead_id": "lead-1",
      "notes": "Source: Website"
    }
  ]
  ```

---

### 3. Create Task

- **Method**: `POST`
- **URL**: `/tasks`

### Description

Create a new task linked to a lead. In normal operation, tasks are created by the sync service based on Google Sheet leads, but you can also create tasks manually for testing.

### Request

- **Headers**
  - `Content-Type: application/json`

- **Body (JSON)**

  ```json
  {
    "title": "Follow up with Alice Example",
    "status": "TODO",
    "lead_id": "lead-1",
    "notes": "Source: Website"
  }
  ```

  - **`title`** (string, required): Short description of the task.
  - **`status`** (string, required): One of `"TODO"`, `"IN_PROGRESS"`, `"DONE"`. Defaults to `"TODO"` if omitted.
  - **`lead_id`** (string, required): ID of the corresponding lead in Google Sheets (matches the `id` column).
  - **`notes`** (string, optional): Additional notes.

### Responses

- **201 Created**

  ```json
  {
    "id": "generated-uuid-here",
    "title": "Follow up with Alice Example",
    "status": "TODO",
    "lead_id": "lead-1",
    "notes": "Source: Website"
  }
  ```

- **422 Unprocessable Entity**

  - Validation error if required fields are missing or invalid.

---

### 4. Get Task by ID

- **Method**: `GET`
- **URL**: `/tasks/{task_id}`

### Description

Retrieve a single task by its unique `id`.

### Path Parameters

- **`task_id`** (string, required): UUID of the task.

### Request

- **Headers**: none required
- **Body**: _none_

### Responses

- **200 OK**

  ```json
  {
    "id": "4a4b4e1d-4f8b-4a3a-8ab8-0f8db21fcb1c",
    "title": "Follow up with Alice Example",
    "status": "TODO",
    "lead_id": "lead-1",
    "notes": "Source: Website"
  }
  ```

- **404 Not Found**

  ```json
  {
    "detail": "Task not found"
  }
  ```

---

### 5. Update Task

- **Method**: `PUT`
- **URL**: `/tasks/{task_id}`

### Description

Update selected fields of an existing task. Fields are optional and only the ones you include will be changed.

This endpoint is particularly important for **Task → Lead** updates: changing a task’s `status` here, then running `python -m sync.sync`, will cause the corresponding lead’s status in Google Sheets to be updated.

### Path Parameters

- **`task_id`** (string, required): UUID of the task to update.

### Request

- **Headers**
  - `Content-Type: application/json`

- **Body (JSON)** – any combination of these fields:

  ```json
  {
    "title": "Follow up with Alice Example (updated)",
    "status": "DONE",
    "notes": "Demo completed successfully"
  }
  ```

  - **`title`** (string, optional): New title.
  - **`status`** (string, optional): New status (`"TODO"`, `"IN_PROGRESS"`, `"DONE"`).
  - **`notes`** (string, optional): New notes.

### Responses

- **200 OK**

  ```json
  {
    "id": "4a4b4e1d-4f8b-4a3a-8ab8-0f8db21fcb1c",
    "title": "Follow up with Alice Example (updated)",
    "status": "DONE",
    "lead_id": "lead-1",
    "notes": "Demo completed successfully"
  }
  ```

- **404 Not Found**

  ```json
  {
    "detail": "Task not found"
  }
  ```

- **422 Unprocessable Entity**

  - Validation error if body is invalid.

---

### 6. Get Tasks by Lead ID

- **Method**: `GET`
- **URL**: `/tasks/by-lead/{lead_id}`

### Description

Return all tasks associated with a specific lead. This is useful when you know a `lead_id` from Google Sheets and want to inspect all related tasks.

> **Important:** For the actual two-way sync, **only the task whose `id` is stored in the lead's `task_id` column is considered the canonical task for that lead**.  
> Other tasks that happen to use the same `lead_id` will be ignored by the Task → Lead sync logic to avoid conflicting updates.

### Path Parameters

- **`lead_id`** (string, required): Lead ID corresponding to the `id` column in the Google Sheet.

### Request

- **Headers**: none required
- **Body**: _none_

### Responses

- **200 OK**

  ```json
  [
    {
      "id": "4a4b4e1d-4f8b-4a3a-8ab8-0f8db21fcb1c",
      "title": "Follow up with Alice Example",
      "status": "DONE",
      "lead_id": "lead-1",
      "notes": "Demo completed successfully"
    }
  ]
  ```

---

### 7. Using Postman

### Suggested Environment Variables

Create a Postman environment with:

- **`base_url`** = `http://localhost:8000`

Then define requests using `{{base_url}}`:

- `GET {{base_url}}/health`
- `GET {{base_url}}/tasks`
- `POST {{base_url}}/tasks`
- `GET {{base_url}}/tasks/{{task_id}}`
- `PUT {{base_url}}/tasks/{{task_id}}`
- `GET {{base_url}}/tasks/by-lead/{{lead_id}}`

You can store `task_id` and `lead_id` as environment or collection variables for convenience.

### Example Flow for Task → Lead Update

1. **List tasks**: `GET {{base_url}}/tasks` and pick a `task_id` and `lead_id`.  
   Ideally, use the **task whose `id` matches the `task_id` value in the Google Sheet** for that lead.
2. **Update task status** via Postman:

   - `PUT {{base_url}}/tasks/{{task_id}}`
   - Body:

     ```json
     {
       "status": "DONE"
     }
     ```

3. **Run the sync script** in your terminal:

   ```bash
   python -m sync.sync
   ```

4. **Check the Google Sheet**: the row where `id == lead_id` should now have its `status` updated based on the canonical task’s status (e.g. `DONE` → `QUALIFIED`).


