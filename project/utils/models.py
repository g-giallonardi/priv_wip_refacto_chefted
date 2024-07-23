from pydantic import BaseModel

class Recipe(BaseModel):
    id: int
    name: str = 'Jane Doe'