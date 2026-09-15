from app.modules.assessment.config import GradeConfig
from app.modules.assessment.schemas import AssessmentResult
from app.modules.candidate.schemas import CandidateProfile
from app.modules.jobs.models import JobPosting
from app.modules.matching.schemas import MatchResult

PROMPT_VERSION = "assessment-v1"


def fake_assessment(
    job: JobPosting, candidate: CandidateProfile, match: MatchResult, config: GradeConfig
) -> AssessmentResult:
    missing = match.missing_skills
    matched = match.matched_core_skills + match.matched_secondary_skills
    candidate_skills = {skill.casefold() for skill in candidate.core_skills + candidate.secondary_skills}
    preferred_matched = [skill for skill in job.preferred_skills if skill.casefold() in candidate_skills]
    preferred_missing = [skill for skill in job.preferred_skills if skill.casefold() not in candidate_skills]
    do_not_claim = [f"Do not claim experience with {skill} unless it is in the profile." for skill in missing]
    result = AssessmentResult(
        grade=config.grade,
        fit_score=match.score,
        verdict=match.recommendation,
        concise_summary=f"{job.title} received a deterministic fit score of {match.score}/100.",
        required_matched=matched,
        required_missing=missing,
        preferred_matched=preferred_matched,
        preferred_missing=preferred_missing,
        blockers=[f"Missing required skill: {skill}" for skill in missing],
        risks=["Some vacancy details may be unknown from the supplied input."],
        unknowns=["Employer hiring process"] if config.grade >= 1 else [],
        candidate_strengths=matched,
        cv_emphasis=[f"Emphasize {skill} only as present in the candidate profile." for skill in matched],
        cv_improvements=["Reorder existing truthful experience to emphasize the matched skills."],
        do_not_claim=do_not_claim,
        detailed_fit_explanation=(
            f"The authoritative deterministic score is {match.score}/100. "
            "The assessment does not replace that score."
            if config.grade >= 2
            else None
        ),
        hard_requirements=job.required_skills if config.grade >= 2 else [],
        soft_requirements=job.preferred_skills if config.grade >= 2 else [],
        likely_rejection_risks=[f"Unlisted skill: {skill}" for skill in missing]
        if config.grade >= 2
        else [],
        cv_sections_to_emphasize=["Skills", "Projects"] if config.grade >= 2 else [],
        keywords_to_include_if_truthful=matched if config.grade >= 2 else [],
        recruiter_message=(
            f"Hello, I am interested in the {job.title} role. "
            f"My profile includes {', '.join(matched) or 'relevant backend skills'}."
            if config.grade >= 2
            else None
        ),
        application_strategy=("Review the missing requirements before applying." if config.grade >= 2 else None),
        likely_screening_questions=[f"Describe your experience with {skill}." for skill in matched]
        if config.grade >= 2
        else [],
        likely_technical_topics=matched if config.grade >= 2 else [],
        questions_to_prepare=[f"How is {skill} used in this role?" for skill in missing]
        if config.grade >= 2
        else [],
        behavioral_questions=["Describe a relevant backend project."] if config.grade >= 3 else [],
        system_design_topics=["Service boundaries and failure handling"] if config.grade >= 3 else [],
        study_gaps=missing if config.grade >= 3 else [],
        interviewer_questions=["What would success look like in the first 90 days?"] if config.grade >= 3 else [],
    )
    return result
