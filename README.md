# FinZi AI

FinZi AI is a proper Fintech Web App designed to help users manage their finances.

## Prerequisites

- **Python 3.8+** must be installed and added to your system PATH.

## Setup Instructions

1.  **Install Dependencies**
    Open a terminal in this directory and run:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Environment Setup**
    The project is pre-configured to use a local SQLite database for instant runnability.
    - Configuration file: `backend/.env`

## How to Run

1.  **Start the Backend & Frontend**
    Double-click the `run_backend.bat` file.
    *(Or run `run_backend.bat` from the terminal)*

2.  **Access the Application**
    Open your browser and navigate to:
    [http://localhost:5000](http://localhost:5000)

3.  **Login Credentials**
    Use the following demo credentials to log in:
    - **Phone**: `9786579303`
    - **Password**: `demo123`

## Troubleshooting

- **Import Errors**: If you see "ModuleNotFoundError", ensure you ran `pip install -r requirements.txt`.
- **Database Errors**: If the database is missing, the backend will automatically create an empty SQLite database at `backend/data/dev_transactions.db`. You can use `backend/generate_synthetic_data.py` to populate it if needed (run `python -m backend.generate_synthetic_data` from root).
