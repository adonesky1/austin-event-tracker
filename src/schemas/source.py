from pydantic import BaseModel


class SourceHealthSchema(BaseModel):
    source_name: str
    status: str
    events_found: int = 0
    errors: str | None = None
