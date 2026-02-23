# TIMESTAMP: 2026-02-23 14:55:00
import httpx
import os
import time

API_URL = 'http://localhost:8001/v2/memories/'
HEADERS = {'X-API-Key': 'test-key', 'X-Tenant-Id': '00000000-0000-0000-0000-000000000000'}
FRONTEND_ROOT = '/mnt/extra_storage/dreamsoft_factory/frontend/'
CHUNK_SIZE = 2500

def ingest_file(filename):
    target_path = None
    for root, dirs, files in os.walk(FRONTEND_ROOT):
        if filename in files:
            target_path = os.path.join(root, filename)
            break
    
    if not target_path:
        print("File " + filename + " not found!")
        return

    with open(target_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    chunks = [content[i:i+CHUNK_SIZE] for i in range(0, len(content), CHUNK_SIZE)]
    print("File " + filename + ": " + str(len(content)) + " chars, " + str(len(chunks)) + " chunks.")
    
    for idx, chunk in enumerate(chunks):
        # Stable content without f-string newlines
        header = "FILE: " + filename + " (chunk " + str(idx) + ")"
        full_content = header + chr(10) + chr(10) + chunk
        
        payload = {
            "content": full_content,
            "layer": "semantic",
            "tags": ["modernization_v3", "source_code", "logic"],
            "metadata": {
                "file": filename,
                "chunk_index": idx,
                "total_chunks": len(chunks)
            }
        }
        httpx.post(API_URL, json=payload, headers=HEADERS, timeout=30.0)
        if idx % 10 == 0: print("  -> " + str(idx) + "/" + str(len(chunks)) + " ingested.")

if __name__ == '__main__':
    giants = ['CalcCtrl.js', 'calc.html', 'CartWidgetService.js', 'cart.html', 'ConfigureProjectCtrl.js']
    for g in giants:
        ingest_file(g)
