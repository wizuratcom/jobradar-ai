from app.modules.analysis.schemas import JobAnalysisResult
from app.modules.candidate.schemas import CandidateProfile
from app.modules.jobs.models import JobPosting
from app.modules.matching.schemas import MatchResult


class FakeLLMProvider:
    """A deterministic provider for local development and automated tests."""

    provider_name = "fake"
    model_name = "fake-v1"

    async def analyze_job(
        self,
        job: JobPosting,
        candidate: CandidateProfile,
        deterministic_match: MatchResult,
    ) -> JobAnalysisResult:
        strengths = (
            deterministic_match.matched_core_skills
            + deterministic_match.matched_secondary_skills
        )
        gaps = deterministic_match.missing_skills
        candidate_skills = candidate.core_skills + candidate.secondary_skills
        cv_emphasis = [
            f"Mention {skill} only as listed in the candidate profile."
            for skill in deterministic_match.matched_core_skills
        ]
        if not cv_emphasis:
            cv_emphasis = ["Keep the CV factual and focus on explicitly listed candidate skills."]
        recruiter_skills = ", ".join(candidate_skills[:4]) or "the listed candidate profile"
        risk_factors = (
            [f"The job requires skills not listed in the profile: {', '.join(gaps)}."]
            if gaps
            else []
        )
        return JobAnalysisResult(
            recommendation=deterministic_match.recommendation,
            summary=(
                f"Deterministic score is {deterministic_match.score}/100 for {job.title}. "
                "This optional analysis does not change that score."
            ),
            strengths=strengths,
            gaps=gaps,
            risk_factors=risk_factors,
            cv_emphasis=cv_emphasis,
            recruiter_message=(
                f"Hello, I am interested in the {job.title} role. My candidate profile lists "
                f"{recruiter_skills}; I would welcome a conversation about the role's requirements."
            ),
            interview_topics=deterministic_match.matched_core_skills or candidate.core_skills[:3],
            questions_to_prepare=[
                f"How does this role evaluate {skill}?" for skill in gaps
            ]
            or ["Which project outcomes matter most during the first months in this role?"],
        )
