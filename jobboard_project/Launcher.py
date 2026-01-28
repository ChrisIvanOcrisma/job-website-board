import subprocess
import webbrowser
import os
import sys
import time

# Prevent multiple runs
if os.environ.get("RUN_MAIN") != "true":

    # Path depende kung EXE or script
    if getattr(sys, "frozen", False):
        BASE_DIR = os.path.dirname(sys.executable)
    else:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    MANAGE_PY = os.path.join(BASE_DIR, "manage.py")

    CREATE_NO_WINDOW = 0x08000000

    # Run Django server - NO CMD WINDOW
    subprocess.Popen(
        [
            sys.executable,
            MANAGE_PY,
            "runserver",
            "127.0.0.1:8000",
            "--noreload"
        ],
        cwd=BASE_DIR,
        creationflags=CREATE_NO_WINDOW,
        env={**os.environ, "RUN_MAIN": "true"}
    )

    # Wait for server to start
    time.sleep(3)

    # Open default browser - MAIN PAGE ONLY
    try:
        webbrowser.get('windows-default').open("http://127.0.0.1:8000/")
    except:
        webbrowser.open("http://127.0.0.1:8000/")