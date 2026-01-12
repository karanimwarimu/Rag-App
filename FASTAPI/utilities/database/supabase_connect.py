import asyncpg
import os 
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__) , ".env.DB")
load_dotenv(dotenv_path=env_path)

DB_CONFIG = {
    "host": os.environ["SUPABASE_DB_HOST"],
    "port": int(os.environ.get("SUPABASE_DB_PORT", 5432)),
    "database": os.environ.get("SUPABASE_DB_NAME", "postgres"),
    "user": os.environ["SUPABASE_DB_USER"],
    "password": os.environ["SUPABASE_DB_PASSWORD"],
    #"pool_mode" :os.environ["SUPABASE_DB_POOLMODE"]
}

async def db_connect() :
    return await asyncpg.connect(**DB_CONFIG)