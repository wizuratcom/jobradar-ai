"""Deterministic, bounded candidate context for Grade 2/3 assessment prompts."""

import json
from dataclasses import dataclass

from app.core.config import Settings
from app.modules.candidate.models import CandidateEvidence, CandidateProject
from app.modules.candidate.schemas import CandidateProfile
from app.modules.jobs.models import JobPosting
from app.modules.matching.schemas import MatchResult
from app.modules.matching.service import _candidate_match, _skill_key


def _compact(value: str, limit: int) -> str:
    value = " ".join(value.split())
    return value if len(value) <= limit else f"{value[: limit - 1].rstrip()}…"


@dataclass(frozen=True)
class CandidateAssessmentContext:
    grade: int
    candidate_facts: dict[str, object]
    projects: list[dict[str, object]]
    evidence: list[dict[str, object]]
    missing_requirements: list[str]
    selected_evidence_ids: set[int]
    character_count: int

    def prompt_payload(self) -> dict[str, object]:
        return {
            "candidate_facts": self.candidate_facts,
            "candidate_projects": self.projects,
            "candidate_evidence": self.evidence,
            "candidate_requirement_gaps": self.missing_requirements,
        }


class CandidateContextBuilder:
    """Select only relevant, user-owned facts; never use AI or implicit inference."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def build(
        self,
        *,
        profile: CandidateProfile,
        projects: list[CandidateProject],
        evidence: list[CandidateEvidence],
        job: JobPosting,
        match: MatchResult,
        grade: int,
    ) -> CandidateAssessmentContext:
        if grade not in {2, 3}:
            raise ValueError("Candidate assessment context is only valid for Grade 2 or 3.")
        required = {_skill_key(item) for item in job.required_skills or []}
        preferred = {_skill_key(item) for item in job.preferred_skills or []}
        stack = {_skill_key(item) for item in job.stack_skills or []}
        candidate_by_key = {
            _skill_key(item): item for item in profile.core_skills + profile.secondary_skills
        }
        for skill in profile.skills:
            candidate_by_key.setdefault(_skill_key(skill.canonical_name or skill.name), skill.name)
        for capability in profile.capabilities:
            candidate_by_key.setdefault(_skill_key(capability.name), capability.name)
        relevant_keys = required | preferred | stack
        matching_facts = [
            _compact(candidate_by_key[key], 120)
            for key in sorted(candidate_by_key)
            if key in relevant_keys
            or any(
                _candidate_match(requirement, {key: candidate_by_key[key]})
                for requirement in job.required_skills
            )
        ][:30]
        linked_evidence_ids = {
            evidence_id
            for skill in profile.skills
            if _skill_key(skill.canonical_name or skill.name) in relevant_keys
            for evidence_id in skill.evidence_ids
        } | {
            evidence_id
            for capability in profile.capabilities
            if _skill_key(capability.name) in relevant_keys
            for evidence_id in capability.evidence_ids
        }
        max_projects = (
            self.settings.candidate_context_grade3_max_projects
            if grade == 3
            else self.settings.candidate_context_grade2_max_projects
        )
        max_evidence = (
            self.settings.candidate_context_grade3_max_evidence
            if grade == 3
            else self.settings.candidate_context_grade2_max_evidence
        )
        total_limit = (
            self.settings.candidate_context_grade3_max_total_chars
            if grade == 3
            else self.settings.candidate_context_grade2_max_total_chars
        )
        candidate_facts: dict[str, object] = {
            "target_titles": [_compact(value, 120) for value in profile.desired_titles[:5]],
            "relevant_skills_and_capabilities": matching_facts,
            "experience": {
                "backend_experience_text": _compact(
                    profile.experience.backend_experience_text or "", 600
                )
                or None,
                "backend_experience_months": profile.experience.backend_experience_months,
                "commercial_backend_experience": profile.experience.commercial_backend_experience,
            },
            "languages": [item.model_dump() for item in profile.languages[:10]],
            "work_preferences": {
                "preferred_remote": profile.preferred_remote,
                "preferred_work_modes": profile.preferred_work_modes,
            },
        }
        ranked_evidence = sorted(
            (
                (self._evidence_score(item, required, preferred, stack, linked_evidence_ids), item)
                for item in evidence
            ),
            key=lambda pair: (-pair[0], pair[1].id),
        )
        ranked_projects = sorted(
            ((self._project_score(item, required, preferred, stack), item) for item in projects),
            key=lambda pair: (-pair[0], pair[1].id),
        )
        selected_projects: list[dict[str, object]] = []
        selected_evidence: list[dict[str, object]] = []

        def fits(value: dict[str, object]) -> bool:
            trial = {
                "candidate_facts": candidate_facts,
                "candidate_projects": selected_projects + [value]
                if "project" in value
                else selected_projects,
                "candidate_evidence": selected_evidence + [value]
                if "evidence_type" in value
                else selected_evidence,
                "candidate_requirement_gaps": match.missing_required_requirements,
            }
            return len(json.dumps(trial, ensure_ascii=False, default=str)) <= total_limit

        for score, item in ranked_evidence:
            if score <= 0 or len(selected_evidence) >= max_evidence:
                continue
            compact = self._compact_evidence(item, required | preferred | stack)
            if fits(compact):
                selected_evidence.append(compact)
        for score, item in ranked_projects:
            if score <= 0 or len(selected_projects) >= max_projects:
                continue
            compact = self._compact_project(item, required | preferred | stack)
            if fits(compact):
                selected_projects.append(compact)
        payload = {
            "candidate_facts": candidate_facts,
            "candidate_projects": selected_projects,
            "candidate_evidence": selected_evidence,
            "candidate_requirement_gaps": match.missing_required_requirements,
        }
        return CandidateAssessmentContext(
            grade=grade,
            candidate_facts=candidate_facts,
            projects=selected_projects,
            evidence=selected_evidence,
            missing_requirements=match.missing_required_requirements,
            selected_evidence_ids={
                item["id"] for item in selected_evidence if isinstance(item.get("id"), int)
            },
            character_count=len(json.dumps(payload, ensure_ascii=False, default=str)),
        )

    @staticmethod
    def _overlap(
        values: list[str], required: set[str], preferred: set[str], stack: set[str]
    ) -> int:
        keys = {_skill_key(value) for value in values}
        return 30 * len(keys & required) + 10 * len(keys & preferred) + 3 * len(keys & stack)

    def _evidence_score(
        self,
        item: CandidateEvidence,
        required: set[str],
        preferred: set[str],
        stack: set[str],
        linked: set[int],
    ) -> int:
        return (
            self._overlap(item.technologies or [], required, preferred, stack)
            + self._overlap(item.capabilities or [], required, preferred, stack)
            + (100 if item.id in linked else 0)
        )

    def _project_score(
        self, item: CandidateProject, required: set[str], preferred: set[str], stack: set[str]
    ) -> int:
        return self._overlap(item.technologies or [], required, preferred, stack) + self._overlap(
            item.capabilities or [], required, preferred, stack
        )

    def _compact_evidence(self, item: CandidateEvidence, relevant: set[str]) -> dict[str, object]:
        return {
            "id": item.id,
            "evidence_type": item.evidence_type,
            "summary": _compact(
                f"{item.title}: {item.description}",
                self.settings.candidate_context_max_evidence_chars,
            ),
            "skills": [value for value in item.technologies or [] if _skill_key(value) in relevant],
            "capabilities": [
                value for value in item.capabilities or [] if _skill_key(value) in relevant
            ],
        }

    def _compact_project(self, item: CandidateProject, relevant: set[str]) -> dict[str, object]:
        return {
            "id": item.id,
            "summary": _compact(
                f"{item.title}: {item.description}",
                self.settings.candidate_context_max_project_chars,
            ),
            "skills": [value for value in item.technologies or [] if _skill_key(value) in relevant],
            "capabilities": [
                value for value in item.capabilities or [] if _skill_key(value) in relevant
            ],
        }
