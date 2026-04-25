<<<<<<< HEAD
import subprocess
import sys
import threading
import time


def run_backend():
    print("Starting FastAPI backend on port 8000...")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ]
    )


def run_frontend():
    print("Starting Streamlit frontend...")
    subprocess.run([sys.executable, "-m", "streamlit", "run", "frontend/app.py"])


def main():
    backend_thread = threading.Thread(target=run_backend, daemon=True)
    backend_thread.start()
    time.sleep(2)

    frontend_thread = threading.Thread(target=run_frontend, daemon=True)
    frontend_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down StockFlow AI...")
        sys.exit(0)


if __name__ == "__main__":
    main()
=======
import subprocess
import sys
import threading
import time


def run_backend():
    print("Starting FastAPI backend on port 8000...")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ]
    )


def run_frontend():
    print("Starting Streamlit frontend...")
    subprocess.run([sys.executable, "-m", "streamlit", "run", "frontend/app.py"])


def main():
    backend_thread = threading.Thread(target=run_backend, daemon=True)
    backend_thread.start()
    time.sleep(2)

    frontend_thread = threading.Thread(target=run_frontend, daemon=True)
    frontend_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down StockFlow AI...")
        sys.exit(0)


if __name__ == "__main__":
    main()
>>>>>>> d32bb63 (Initial commit)
