import time
import os
import subprocess
import urllib.request
import json

# Configuration
API_URL = 'http://localhost:8001/v2/memories/'
HEADERS = {'X-API-Key': 'test-key', 'X-Tenant-Id': '00000000-0000-0000-0000-000000000000'}
WORK_DIR = '/mnt/extra_storage/RAE-agentic-memory/agent_hive/work_dir/components/'
COMPOSE_DIR = '/mnt/extra_storage/RAE-agentic-memory/agent_hive/'

def log_to_rae(msg, tags=[]):
    payload = {"content": f"[SUPERVISOR] {msg}", "layer": "reflective", "tags": ["supervisor_log"] + tags}
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(API_URL, data=data, headers={'Content-Type': 'application/json', **HEADERS}, method='POST')
        urllib.request.urlopen(req, timeout=10)
    except: pass

def get_file_count():
    try:
        return len([f for f in os.listdir(WORK_DIR) if f.endswith('.tsx')])
    except: return 0

def check_factory_alive():
    try:
        # Check if container is running using explicit name
        res = subprocess.check_output("docker ps --filter name=hive-builder --format '{{.Status}}'", shell=True)
        return "Up" in res.decode()
    except: return False

def restart_factory():
    log_to_rae("Stall detected! Restarting hive-builder...", ["action_required"])
    # MUST change directory to where docker-compose.hive.yml is!
    subprocess.run(f"cd {COMPOSE_DIR} && docker compose -f docker-compose.hive.yml restart hive-builder", shell=True)

last_count = get_file_count()
stalls = 0

print("🕵️ Supervisor v2 active. Monitoring Dreamsoft Factory...")
log_to_rae("Supervisor v2 started. Paths corrected.")

while True:
    time.sleep(120)
    current_count = get_file_count()
    is_alive = check_factory_alive()
    
    if current_count > last_count:
        log_to_rae(f"Progress: {current_count} files (+{current_count - last_count})", ["progress"])
        stalls = 0
        last_count = current_count
    else:
        stalls += 1
        print(f"Stall check {stalls}/3")
        if stalls >= 3:
            restart_factory()
            stalls = 0
