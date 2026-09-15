from dataclasses import dataclass

from app.core.config import Settings


@dataclass(frozen=True)
class GradeConfig:
    grade: int
    model: str | None
    reasoning: str | None


def grade_config(grade: int, settings: Settings) -> GradeConfig:
    if grade == 0:
        return GradeConfig(0, None, None)
    models = {1: settings.ai_grade1_model, 2: settings.ai_grade2_model, 3: settings.ai_grade3_model}
    reasoning = {
        1: settings.ai_grade1_reasoning,
        2: settings.ai_grade2_reasoning,
        3: settings.ai_grade3_reasoning,
    }
    if grade not in models:
        raise ValueError("grade must be between 0 and 3")
    return GradeConfig(grade, models[grade], reasoning[grade])
