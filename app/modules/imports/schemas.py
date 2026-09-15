from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator


class JobImportRequest(BaseModel):
    input_type: Literal["text", "json", "url"]
    text: str | None = Field(default=None, min_length=1)
    url: HttpUrl | None = None
    payload: dict[str, Any] | None = None
    grade: int | None = Field(default=None, ge=0, le=3)

    @model_validator(mode="after")
    def input_matches_type(self) -> "JobImportRequest":
        if self.input_type == "text" and not self.text:
            raise ValueError("text is required for input_type=text")
        if self.input_type == "url" and not self.url:
            raise ValueError("url is required for input_type=url")
        if self.input_type == "json" and self.payload is None:
            raise ValueError("payload is required for input_type=json")
        return self


class ImportWarning(BaseModel):
    message: str


class JobImportResponse(BaseModel):
    job: Any
    source: dict[str, Any]
    match: Any
    assessment: Any | None = None
    warnings: list[str] = Field(default_factory=list)
