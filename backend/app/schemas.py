from pydantic import BaseModel
from typing import List, Optional

class OnboardingRequest(BaseModel):
    genres: List[str]
    keywords: str

class RatingCreate(BaseModel):
    userId: str
    movieId: int
    rating: float

class MovieCreate(BaseModel):
    title: str
    genres: str
