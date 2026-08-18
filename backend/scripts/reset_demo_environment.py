from __future__ import annotations

import argparse
import asyncio
import shutil
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.core.config import get_settings
from app.models.base import Base


def reset_database() -> None:
    settings = get_settings()
    sync_url = settings.database_url.replace("+asyncpg", "+psycopg")
    engine = create_engine(sync_url, pool_pre_ping=True)
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())
    engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset the KMRL synthetic demo environment.")
    parser.add_argument("--yes", action="store_true", help="Confirm destructive demo reset.")
    args = parser.parse_args()
    if not args.yes:
        raise SystemExit("This clears demo data. Re-run with --yes to confirm.")
    settings = get_settings()
    storage = Path(settings.storage_path)
    if not storage.is_absolute():
        storage = ROOT / storage
    if storage.exists():
        shutil.rmtree(storage)
    reset_database()
    subprocess.run([sys.executable, str(ROOT / "scripts" / "seed.py")], check=True, cwd=ROOT)
    subprocess.run(["python3", str(ROOT / "scripts" / "generate_demo_corpus.py")], check=True, cwd=ROOT)
    asyncio.run(_seed_corpus())
    print("demo environment reset and fully reprocessed")


async def _seed_corpus() -> None:
    scripts_dir = str(ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from seed_demo_corpus import main as seed_main
    await seed_main()


if __name__ == "__main__":
    main()
