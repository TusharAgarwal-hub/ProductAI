from pydantic import BaseModel

class ProductTextRequest(BaseModel):
    text: str
