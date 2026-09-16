import httpx
import pytest

from app.main import app


@pytest.mark.asyncio
async def test_one_line_text_accepts_plain_text_without_json_escaping() -> None:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/tools/one-line-text",
            content="Senior Python Developer\n\nRequirements:\n  Python\tFastAPI",
            headers={"content-type": "text/plain"},
        )
    assert response.status_code == 200
    assert response.json() == {"text": "Senior Python Developer Requirements: Python FastAPI"}


@pytest.mark.asyncio
async def test_one_line_text_rejects_whitespace_only_body() -> None:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/tools/one-line-text",
            content=" \n\t ",
            headers={"content-type": "text/plain"},
        )
    assert response.status_code == 422
