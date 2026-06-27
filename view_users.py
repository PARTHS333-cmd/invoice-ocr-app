import asyncio
from app.db.database import get_db
from app.db.models import User
from sqlalchemy import select

async def view_all_users():
    print("--- Fetching Registered Users ---")
    async for db in get_db():
        result = await db.execute(select(User))
        users = result.scalars().all()
        
        if not users:
            print("No accounts found in the database.")
            return
            
        for user in users:
            print(f"ID: {user.id}")
            print(f"Username: {user.username}")
            print(f"Email: {user.email}")
            print(f"Hashed Password: {user.hashed_password}")
            print("-" * 30)

if __name__ == "__main__":
    asyncio.run(view_all_users())
