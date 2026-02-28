import httpx
import json
import time
import os
import subprocess

API_URL = os.getenv('RAE_API_URL', 'http://localhost:8000/v2/memories/')
DB_CMD = "psql -h postgres -U rae -d rae -t -c"
OLLAMA_URL = 'http://ollama-dev:11434/api/generate'
MODEL = 'qwen2.5:14b'
HEADERS = {'X-API-Key': 'test-key', 'X-Tenant-Id': '00000000-0000-0000-0000-000000000000'}
EXPORT_DIR = '/app/agent_hive/work_dir/export_nextjs/'
NL = chr(10)

os.makedirs(EXPORT_DIR, exist_ok=True)

def get_graph_context(memory_id):
    try:
        q = f"SELECT m.content FROM memory_neighbors n JOIN memories m ON n.target_id = m.id WHERE n.source_id = '{memory_id}' LIMIT 3;"
        res = subprocess.check_output(f'PGPASSWORD=rae_password {DB_CMD} "{q}"', shell=True)
        return res.decode().strip()
    except Exception as e:
        return ""

def process_hive():
    try:
        resp = httpx.get(API_URL + '?layer=semantic&limit=10', headers=HEADERS, timeout=10.0)
        mems = resp.json().get('results', [])
        
        if not mems: return

        mem_to_process = None
        for m in mems:
            if 'processed' not in m.get('tags', []) and 'escalated' not in m.get('tags', []):
                mem_to_process = m
                break
                
        if not mem_to_process:
            return

        mid = mem_to_process['id']
        tags = mem_to_process.get('tags', [])
        metadata = mem_to_process.get('metadata', {})
        source = mem_to_process['content']
        
        s_name = metadata.get('service') or metadata.get('file') or f"component_{str(mid)[:8]}"
        if not s_name.endswith('.tsx') and not s_name.endswith('.ts'):
            s_name = s_name.split('.')[0] + '.tsx'
            
        print(f"ENGINE v1-LTS: Modernizacja {s_name}...")
        
        context = get_graph_context(mid)
        context_prompt = f"{NL}{NL}Context from Knowledge Graph:{NL}{context}" if context else ""
        prompt = f"Convert the following code to a modern Next.js TSX component. Return ONLY valid TypeScript code without markdown blocks.{NL}{NL}Code:{NL}{source}{context_prompt}"
        
        payload = {'model': MODEL, 'prompt': prompt, 'stream': False}
        
        try:
            res = httpx.post(OLLAMA_URL, json=payload, timeout=300.0)
            final = res.json().get('response', '').strip()
            
            if final.startswith('```'):
                lines = final.split(NL)
                final = NL.join(lines[1:-1]) if lines[-1].startswith('```') else NL.join(lines[1:])
                
            target_file = os.path.join(EXPORT_DIR, s_name)
            with open(target_file, 'w') as f:
                f.write(final)
                
            new_tags = [t for t in tags if t != 'pending'] + ['processed', 'review']
            httpx.patch(API_URL + mid, json={'tags': new_tags}, headers=HEADERS, timeout=10.0)
            
            print(f"SUKCES: {s_name} zapisany (Graf Context: {'Tak' if context else 'Nie'}).")
            
        except httpx.ReadTimeout:
            print(f"TIMEOUT Ollama dla {s_name}. Oznaczam jako processed.")
            new_tags = tags + ['processed', 'timeout']
            httpx.patch(API_URL + mid, json={'tags': new_tags}, headers=HEADERS, timeout=10.0)
            
    except Exception as e:
        print(f"BLAD silnika: {e}")

if __name__ == "__main__":
    print("Hive Engine v1.0 LTS (Oracle Deep Graph) START")
    while True:
        process_hive()
        time.sleep(3)
