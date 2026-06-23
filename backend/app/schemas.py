from pydantic import BaseModel
from typing import List, Optional

class OnboardingRequest(BaseModel):
    genres: List[str]
    keywords: str
    userId: Optional[str] = None  # if provided, seed ratings under this account

class RatingCreate(BaseModel):
    userId: str
    movieId: int
    rating: float

class MovieCreate(BaseModel):
    title: str
    genres: str

class UserAuth(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    token: str
    username: str
