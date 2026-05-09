from pydantic import BaseModel, Field


class AiQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    user_type: str = Field(default="beginner", pattern="^(beginner|intermediate|advanced)$")
    user_id: str = Field(default="demo")


class AiQueryResponse(BaseModel):
    answer_markdown: str
    structured: dict

