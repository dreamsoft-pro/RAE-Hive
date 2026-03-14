import asyncio
import asyncpg
from qdrant_client import AsyncQdrantClient
import os
import json

async def validate():
    print("Starting SQL-Qdrant Sync Validation...")
    
    # 1. Connect to Postgres
    conn = await asyncpg.connect(
        host='localhost', 
        port=5432, 
        user='rae', 
        password='rae_password', 
        database='rae'
    )
    
    # 2. Connect to Qdrant
    qdrant = AsyncQdrantClient(host='localhost', port=6333)
    
    # 3. Fetch all IDs from SQL
    rows = await conn.fetch("SELECT id FROM memories")
    sql_ids = [str(r['id']) for r in rows]
    print(f"Found {len(sql_ids)} records in Postgres.")
    
    # 4. Check each ID in Qdrant
    missing_in_qdrant = []
    for m_id in sql_ids:
        try:
            res = await qdrant.retrieve(collection_name='memories', ids=[m_id])
            if not res:
                missing_in_qdrant.append(m_id)
        except Exception as e:
            missing_in_qdrant.append(m_id)
            
    print(f"Validation complete. Missing in Qdrant: {len(missing_in_qdrant)}")
    
    report = {
        'total_sql': len(sql_ids),
        'missing_vector_count': len(missing_in_qdrant),
        'missing_ids': missing_in_qdrant
    }
    
    with open('agent_hive/work_dir/sync_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    await conn.close()

if __name__ == '__main__':
    asyncio.run(validate())
