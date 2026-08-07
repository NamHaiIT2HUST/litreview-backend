import asyncio
import uuid
from src.database import AsyncSessionLocal
from src.models.db_models import Project

async def seed_project():
    async with AsyncSessionLocal() as db:
        project_id = "00000000-0000-0000-0000-000000000001"
        
        # Check if exists
        result = await db.execute(
            __import__('sqlalchemy').select(Project).where(Project.id == project_id)
        )
        if result.scalar_one_or_none():
            print("Default project already exists.")
            return

        new_project = Project(
            id=project_id,
            name='Tác động của sinh viên kiệt sức',
            research_question='Sinh viên kiệt sức ảnh hưởng thế nào đến kết quả học tập?',
            research_field='Giáo dục học',
            year_from=2018,
            year_to=2024,
            criteria_include=['Nghiên cứu định lượng', 'Sinh viên đại học'],
            criteria_exclude=['Học sinh phổ thông']
        )
        db.add(new_project)
        await db.commit()
        print("Successfully seeded default project 0000...0001")

if __name__ == "__main__":
    asyncio.run(seed_project())
