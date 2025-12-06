# Flask API Starter Template

A comprehensive starter template for building RESTful APIs with Flask.

## Features

*   **Flask-SQLAlchemy:** For database interactions.
*   **Flask-Migrate:** For database migrations with Alembic.
*   **Flask-Cors:** To handle Cross-Origin Resource Sharing (CORS).
*   **Blueprints:** For modular application structure.
*   **Application Factory:** To create app instances with different configurations.
*   **Environment-based Configuration:** Using `.env` files for easy configuration.

## Project Structure

```
backend/
├── app/
│   ├── blueprints/
│   ├── cli/
│   ├── core/
│   ├── docs/
│   ├── tasks/
│   ├── __init__.py
│   ├── config.py
│   ├── error_handler.py
│   └── extensions.py
├── migrations/
│   ├── versions/
│   ├── alembic.ini
│   ├── env.py
│   ├── README
│   └── script.py.mako
├── tests/
│   ├── __init__.py
│   └── conftest.py
├── .env
├── .env.example
├── .gitignore
├── pytest.ini
├── README.md
├── requirements.txt
└── wsgi.py
```

## Getting Started

### Prerequisites

*   Python 3.12+
*   PostgreSQL (or your preferred database)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd backend
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv env
    source env/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Configuration

1.  **Create a `.env` file:**
    ```bash
    cp .env.example .env
    ```

2.  **Update the environment variables** in the `.env` file with your database credentials and a secret key.

### Running the Application

```bash
flask run
```

## Testing

To run the test suite:

```bash
pytest
```
