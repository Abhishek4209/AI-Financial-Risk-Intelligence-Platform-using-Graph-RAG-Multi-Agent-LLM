import os
import sys
import time
import socket
import subprocess
import webbrowser
from pathlib import Path

from dotenv import load_dotenv


# ============================================================
# PROJECT CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"

# Load the existing .env file from the project root
load_dotenv(PROJECT_ROOT / ".env")

PYTHON_EXE = Path(
    r"C:\Users\USER\anaconda3\envs\ds\python.exe"
)

BACKEND_HOST = "0.0.0.0"
BACKEND_PORT = 8000

FRONTEND_HOST = "0.0.0.0"
FRONTEND_PORT = 5173

DATABASE_HOST = "127.0.0.1"
DATABASE_PORT = 5432
DATABASE_NAME = "financial_risk_db"
DATABASE_USER = "postgres"

FRONTEND_LAN_ORIGIN = "http://10.171.1.112:5173"

BACKEND_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://10.171.1.112:5173/"


# ============================================================
# WINDOWS PROCESS SETTINGS
# ============================================================

CREATE_NEW_CONSOLE = getattr(
    subprocess,
    "CREATE_NEW_CONSOLE",
    0
)


# ============================================================
# CHECK PORT
# ============================================================

def is_port_open(host, port):
    try:
        with socket.create_connection(
            (host, port),
            timeout=2
        ):
            return True
    except OSError:
        return False


def wait_for_port(host, port, timeout=30):
    start_time = time.time()

    while time.time() - start_time < timeout:
        if is_port_open(host, port):
            return True

        time.sleep(1)

    return False


# ============================================================
# START BACKEND
# ============================================================

def start_backend(database_url):
    print("\nStarting FastAPI backend...")

    backend_env = os.environ.copy()

    backend_env["DATABASE_URL"] = database_url

    backend_env["CORS_ALLOWED_ORIGINS"] = (
        "http://localhost:5173,"
        "http://127.0.0.1:5173,"
        f"{FRONTEND_LAN_ORIGIN}"
    )

    backend_env["AUTH_DISABLED"] = "true"

    command = [
        str(PYTHON_EXE),
        "-m",
        "uvicorn",
        "src.api.main:app",
        "--host",
        BACKEND_HOST,
        "--port",
        str(BACKEND_PORT),
        "--reload",
    ]

    subprocess.Popen(
        command,
        cwd=str(PROJECT_ROOT),
        env=backend_env,
        creationflags=CREATE_NEW_CONSOLE,
    )

    if wait_for_port(
        "127.0.0.1",
        BACKEND_PORT,
        timeout=30
    ):
        print("Backend is reachable.")
        print(f"Swagger: {BACKEND_URL}/docs")
        return True

    print(
        "\nBackend did not become reachable within 30 seconds."
    )
    print(
        "Check the backend terminal for Python or database errors."
    )

    return False


# ============================================================
# START FRONTEND
# ============================================================

def start_frontend():
    print("\nStarting React / Vite frontend...")

    package_json = FRONTEND_DIR / "package.json"
    node_modules = FRONTEND_DIR / "node_modules"

    if not package_json.exists():
        print(
            f"Frontend package.json not found:\n{package_json}"
        )
        return False

    if not node_modules.exists():
        print(
            "\nFrontend dependencies are missing."
        )
        print(
            "Run npm install once inside the frontend folder."
        )
        return False

    npm_path = Path(
        r"C:\Program Files\nodejs\npm.cmd"
    )

    if not npm_path.exists():
        print("npm.cmd was not found.")
        return False

    frontend_env = os.environ.copy()

    frontend_env["VITE_API_URL"] = BACKEND_URL

    command = [
        str(npm_path),
        "run",
        "dev",
        "--",
        "--host",
        FRONTEND_HOST,
        "--port",
        str(FRONTEND_PORT),
    ]

    subprocess.Popen(
        command,
        cwd=str(FRONTEND_DIR),
        env=frontend_env,
        creationflags=CREATE_NEW_CONSOLE,
    )

    print("Frontend process started.")
    return True


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("AI FINANCIAL RISK INTELLIGENCE PLATFORM")
    print("Application Startup")
    print("=" * 60)

    # Check required files
    if not PYTHON_EXE.exists():
        print(
            f"\nPython environment not found:\n{PYTHON_EXE}"
        )
        return

    if not FRONTEND_DIR.exists():
        print(
            f"\nFrontend folder not found:\n{FRONTEND_DIR}"
        )
        return

    # Check PostgreSQL without starting or stopping it
    print("\nChecking PostgreSQL...")

    if not is_port_open(
        DATABASE_HOST,
        DATABASE_PORT
    ):
        print(
            "\nPostgreSQL is not reachable on port 5432."
        )
        print(
            "Start your PostgreSQL service and try again."
        )
        return

    print("PostgreSQL server is reachable.")

    # Load DATABASE_URL from .env
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print(
            "DATABASE_URL is missing from your .env file."
        )
        return

    # Start backend
    backend_started = start_backend(database_url)

    if not backend_started:
        print(
            "\nFrontend will not be started because "
            "the backend is not reachable."
        )
        return

    # Start frontend
    frontend_started = start_frontend()

    if not frontend_started:
        return

    # Open application
    print("\nApplication startup completed.")
    print(f"Backend docs: {BACKEND_URL}/docs")
    print(f"Frontend:    {FRONTEND_URL}")

    time.sleep(3)

    webbrowser.open(FRONTEND_URL)


# ============================================================
# APPLICATION ENTRY POINT
# ============================================================

if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        print(
            "\nLauncher interrupted. "
            "Close the backend and frontend terminal windows "
            "to stop their processes."
        )

    except Exception as error:
        print(f"\nStartup error: {error}")