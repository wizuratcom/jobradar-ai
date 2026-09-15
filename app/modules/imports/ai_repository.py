from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.imports.ai_models import AIExtraction
from app.modules.imports.ai_schemas import AIExtractionResult


class AIExtractionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        user_id: int,
        result: AIExtractionResult,
        provider: str,
        model: str | None,
        prompt_version: str,
        input_tokens: int | None,
        cached_input_tokens: int | None,
        output_tokens: int | None,
        reasoning_tokens: int | None,
    ) -> AIExtraction:
        record = AIExtraction(
            user_id=user_id,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            extraction_payload=result.model_dump(mode="json"),
            input_tokens=input_tokens,
            cached_input_tokens=cached_input_tokens,
            output_tokens=output_tokens,
            reasoning_tokens=reasoning_tokens,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record
