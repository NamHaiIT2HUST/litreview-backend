import asyncio
import csv
import os
from sqlalchemy import select
from src.database import AsyncSessionLocal
from src.models.db_models import ScopusSource

async def run():
    print("Starting SCImago Quartile import...")
    file_path = os.path.join("data", "scimagojr.csv")
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        print("Please download it from https://www.scimagojr.com/journalrank.php?out=xls and place it in the data/ folder as scimagojr.csv")
        return

    async with AsyncSessionLocal() as db:
        try:
            count = 0
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';')
                
                # Sometime SCImago uses ',' instead of ';'
                if not reader.fieldnames or 'Issn' not in reader.fieldnames:
                    f.seek(0)
                    reader = csv.DictReader(f, delimiter=',')
                
                for row in reader:
                    issn_str = row.get('Issn', '')
                    quartile = row.get('SJR Best Quartile', '').strip()
                    
                    if not issn_str or not quartile or quartile == '-':
                        continue
                    
                    # Issn column can contain multiple ISSNs separated by comma
                    issns = [i.strip() for i in issn_str.split(',')]
                    
                    for issn in issns:
                        # Find ScopusSource by ISSN
                        result = await db.execute(
                            select(ScopusSource).where(
                                (ScopusSource.issn == issn) | (ScopusSource.eissn == issn)
                            )
                        )
                        source = result.scalar_one_or_none()
                        if source:
                            source.quartile = quartile
                            count += 1
                            break # Move to next row once matched
            
            await db.commit()
            print(f"Successfully updated quartile data for {count} journals.")
        except Exception as e:
            await db.rollback()
            print(f"Error during import: {e}")

if __name__ == "__main__":
    asyncio.run(run())
