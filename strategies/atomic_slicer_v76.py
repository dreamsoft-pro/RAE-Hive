# TIMESTAMP: 2026-02-23 15:20:00
import urllib.request
import json
import os
import time
import re
from pathlib import Path

# v76 - Direct File Slicer (Bypassing DB Integrity Issues)
BASE_API = "http://localhost:8001/v2/memories" 
OUT_DIR = '/mnt/extra_storage/RAE-agentic-memory-agnostic-core/agent_hive/work_dir/components/'
FRONTEND_ROOT = '/mnt/extra_storage/dreamsoft_factory/frontend/'
CHUNK_SIZE = 3000
HEADERS = {'X-API-Key': 'test-key', 'X-Tenant-Id': '00000000-0000-0000-0000-000000000000'}

def log_msg(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def find_file(filename):
    for root, dirs, files in os.walk(FRONTEND_ROOT):
        if filename in files:
            return os.path.join(root, filename)
    return None

def http_req(url, data=None, method='GET'):
    body = json.dumps(data).encode('utf-8') if data else None
    headers = {'Content-Type': 'application/json', **HEADERS} if data else HEADERS
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=300) as f:
            return json.loads(f.read().decode('utf-8'))
    except: return {}

def ask_saas(prompt):
    payload = {"content": "SYSTEM: Code Modernizer\nUSER: " + prompt, "layer": "reflective", "tags": ["hive_call", "gemini-2.5-pro"]}
    res = http_req(BASE_API + "/", payload, 'POST')
    return res.get('message', '')

def process_file_directly(filename):
    log_msg(f"🚀 DIRECT PROCESSING: {filename}")
    f_path = find_file(filename)
    if not f_path:
        log_msg(f"❌ File {filename} not found on disk!")
        return

    folder_name = filename.replace('.js', '_Atomic').replace('.html', '_Atomic')
    base_path = os.path.join(OUT_DIR, folder_name)
    if not os.path.exists(base_path): os.makedirs(base_path)

    with open(f_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    chunks = [content[i:i+CHUNK_SIZE] for i in range(0, len(content), CHUNK_SIZE)]
    log_msg(f"  -> {len(chunks)} chunks created from disk.")

    for i, chunk in enumerate(chunks):
        target_file = os.path.join(base_path, f"chunk_{i:03d}.tsx")
        if os.path.exists(target_file) and os.path.getsize(target_file) > 100:
            continue
            
        log_msg(f"  -> Modernizing chunk {i}/{len(chunks)}...")
        code = ask_saas(f"Modernize this piece to Next.js/TS. OUTPUT ONLY CODE.\nSOURCE:\n{chunk}")
        
        if len(code) > 50:
            if '```' in code:
                try: code = re.search(r'```(?:tsx|ts|js)?\n(.*?)\n```', code, re.DOTALL).group(1).strip()
                except: pass
            with open(target_file, 'w') as f: f.write(code)
            log_msg(f"    ✅ Chunk {i} saved.")
        else:
            log_msg(f"    ❌ Chunk {i} FAILED.")
        
        time.sleep(10)

if __name__ == '__main__':
    # Focus only on the most critical giants first
    giants = ['CalcCtrl.js', 'calc.html', 'CartWidgetService.js', 'cart.html']
    for g in giants:
        process_file_directly(g)
