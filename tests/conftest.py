import os
from pathlib import Path

TEST_ROOT = Path(__file__).parent
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_ROOT / 'test_jobradar.db'}"
os.environ["CANDIDATE_PROFILE_PATH"] = str(TEST_ROOT.parent / "candidate.example.yaml")
