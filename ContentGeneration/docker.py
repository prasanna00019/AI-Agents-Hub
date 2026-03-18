import subprocess
import time
import os

DOCKER_PATH = r"C:\Program Files\Docker\Docker\Docker Desktop.exe"

def start_docker():
    subprocess.Popen([DOCKER_PATH], shell=True)
    
    # Wait until Docker is ready
    for _ in range(30):
        try:
            subprocess.run(["docker", "info"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("Docker is ready")
            return True
        except:
            time.sleep(2)
    
    raise RuntimeError("Docker failed to start")

def is_docker_running():
    try:
        subprocess.run(["docker", "info"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except:
        return False
if not is_docker_running():
    start_docker()
else :
    print("Docker is already running")       