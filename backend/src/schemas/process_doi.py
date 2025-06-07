from pydantic import BaseModel


class ProcessDOISchema(BaseModel):
    doi: str
