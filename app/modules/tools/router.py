from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, status
from pydantic import BaseModel


class OneLineTextResponse(BaseModel):
    text: str


router = APIRouter(prefix="/api/v1/tools", tags=["tools"])


@router.post("/one-line-text", response_model=OneLineTextResponse)
async def one_line_text(
    text: Annotated[str, Body(media_type="text/plain", min_length=1)],
) -> OneLineTextResponse:
    """Collapse any whitespace in pasted text without storing it."""
    normalized = " ".join(text.split())
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Text must contain non-whitespace characters.",
        )
    return OneLineTextResponse(text=normalized)
