import asyncio
import sys
import os

sys.path.append(r"c:\Users\User\OneDrive\Desktop\lablens\backend\src")
os.environ["LABLENS_DATABASE_URL"] = "postgresql+asyncpg://lablens:AZfarpE3FE7rgrJdtsk1WymMxwpdzKDf@dpg-d9loqtf10e5c73e4f3t0-a.oregon-postgres.render.com/lablens_ovai"
os.environ["LABLENS_ENV"] = "production"

from lablens.db.models import User, init_db, get_engine
from lablens.auth.service import AuthService
from sqlalchemy.ext.asyncio import async_sessionmaker

async def test():
    print("Initializing DB...")
    await init_db()
    
    engine = get_engine()
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    print("Attempting to insert user...")
    async with async_session() as db:
        user = User(
            email="syed123@gmail.com",
            hashed_password=AuthService.hash_password("password123"),
            full_name="Syed"
        )
        db.add(user)
        try:
            await db.commit()
            print("SUCCESS!")
        except Exception as e:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
