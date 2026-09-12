from functools import lru_cache

import yaml

from app.core.config import get_settings
from app.modules.candidate.schemas import CandidateProfile


@lru_cache
def load_candidate_profile() -> CandidateProfile:
    path = get_settings().candidate_profile_path
    with path.open(encoding="utf-8") as profile_file:
        contents = yaml.safe_load(profile_file)
    return CandidateProfile.model_validate(contents)
