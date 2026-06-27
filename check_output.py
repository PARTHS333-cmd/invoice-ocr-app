import asyncio
from app.db.database import get_db
from app.db.models import ProcessingTask

async def check_ocr_outputs():
    print("--- Checking OCR Task Outputs ---")
    async for db in get_db():
        result = await db.execute(
            select(ProcessingTask).where(ProcessingTask.status == "completed")
        )
        completed_tasks = result.scalars().all()
        
        if not completed_tasks:
            print("No tasks have saved a completed output yet.")
            return
            
        for task in completed_tasks:
            print(f"Task ID: {task.task_id} (Internal ID: {task.id})")
            print(f"Status: {task.status}")
            print(f"Raw Extracted Data/Result: {task.result}")
            print("-" * 50)

if __name__ == "__main__":
    from sqlalchemy import select
    asyncio.run(check_ocr_outputs())
