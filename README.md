# FunDooNotes API (FastAPI)

A RESTful backend for managing personal notes and labels, built with **FastAPI** and **CSV file persistence**. This project follows **Object-Oriented Programming (OOP)** principles and a **modular repository-service architecture**.

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+
- `pip` (Python package manager)

### 2. Setup & Installation
1. **Clone the repository:**
   ```bash
   git clone https://github.com/nvsingh2001/FunDooNotes_Fastapi.git
   cd FunDooNotes_Fastapi
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # OR
   .venv\Scripts\activate     # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### 3. Running the Server
Start the application using `uvicorn`:
```bash
uvicorn app.main:app --reload
```
The API will be available at: **`http://127.0.0.1:8000`**

### 4. Interactive Documentation
- **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 📂 Project Structure

The project is organized into a modular structure to ensure scalability, testability, and separation of concerns.

```text
app/
├── core/                # Core logic: SecurityService (Auth), Logger configuration
├── repositories/        # Data access layer (User, Note, Label, NoteLabel)
├── routers/             # API endpoint definitions (Auth, Notes, Labels)
├── schemas/             # Pydantic models for request/response validation
├── storage.py           # StorageManager for handling file persistence
└── main.py              # App factory and entry point
data/                    # Directory where CSV data files are persisted
logs/                    # Directory for structured application logs
```

- **Repositories:** Each data entity has its own repository class responsible for CRUD operations on CSV files.
- **SecurityService:** A centralized OOP-based service for password hashing and JWT token management.
- **StorageManager:** Orchestrates all repositories and ensures file consistency.

---

## 🛠 API Reference

### 1. Authentication (`/auth`)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/auth/register` | Create a new user account. |
| `POST` | `/auth/login` | Authenticate and receive a JWT access token. |

### 2. Notes (`/notes`)
*Requires Bearer Token*
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/notes/` | List all notes for the authenticated user. |
| `POST` | `/notes/` | Create a new note. |
| `GET` | `/notes/{id}` | Retrieve a specific note by ID. |
| `PUT` | `/notes/{id}` | Update an existing note. |
| `DELETE` | `/notes/{id}` | Delete a note (cascades to associations). |

### 3. Labels (`/labels`)
*Requires Bearer Token*
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/labels/` | List all labels created by the user. |
| `POST` | `/labels/` | Create a new unique label. |
| `PUT` | `/labels/{id}` | Rename a label. |
| `DELETE` | `/labels/{id}` | Delete a label (detaches from all notes). |

### 4. Note-Label Associations
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/notes/{n_id}/labels/{l_id}` | Attach a label to a note. |
| `DELETE` | `/notes/{n_id}/labels/{l_id}` | Remove a label from a note. |

---

## 🛡 Security
- **JWT Authorization:** Uses `jose` for token generation and `argon2-cffi` for industry-standard password hashing.
- **Resource Ownership:** All endpoints verify that the requesting user owns the resource (Note/Label) they are accessing.
- **Input Validation:** Strict Pydantic v2 models prevent malformed data.

---

## 📝 Features
- **Cascading Deletes:** Deleting a note or label automatically cleans up the associations.
- **Structured Logging:** Uses `Loguru` with console and file-based rotation.
- **Health Monitoring:** `/health` endpoint for uptime checks.
