from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models import Chunk


async def inspect(version_id: str) -> None:
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(select(Chunk).where(Chunk.version_id == version_id).order_by(Chunk.chunk_index))).scalars().all()
        print(f"chunks={len(rows)}")
        for chunk in rows:
            print(f"page={chunk.page_id} section={chunk.section_number or '-'} title={chunk.section_title or '-'} chunk_id={chunk.id} index={chunk.chunk_index} tokens={chunk.token_count} chars={len(chunk.text)} ocr={chunk.ocr_confidence}")
            print(f"  {chunk.text[:300].replace(chr(10), ' ')}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python backend/scripts/inspect_chunks.py VERSION_ID")
    asyncio.run(inspect(sys.argv[1]))
