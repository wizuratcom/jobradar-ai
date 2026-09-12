import os
from pathlib import Path

TEST_ROOT = Path(__file__).parent
sqlite_test_url = f"sqlite+aiosqlite:///{TEST_ROOT / 'test_jobradar.db'}"
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL", sqlite_test_url)
os.environ["CANDIDATE_PROFILE_PATH"] = str(TEST_ROOT.parent / "candidate.example.yaml")
