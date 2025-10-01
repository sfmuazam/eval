# migrate.py
import asyncio
from models import Base, engine

async def run():
    # create_all harus dijalankan di context sync, gunakan run_sync
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("All tables created.")

if __name__ == "__main__":
    asyncio.run(run())