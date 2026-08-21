# Minimal setup.py at root — tells Render this is a Python project
# Actual package is in backend/
import subprocess
subprocess.check_call(["pip", "install", "-r", "requirements.txt"])
