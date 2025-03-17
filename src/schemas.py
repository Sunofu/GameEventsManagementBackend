from pydantic import BaseModel
from datetime import datetime
from datetime import date


class UserCreate(BaseModel):
    UserName: str
    Email: str
    password: str
    isDeveloper: bool

class DeveloperCreate(UserCreate):
        companyName: str
        country: str
        foundationDate: date
        Url: str = ''

class LoginUser(BaseModel):
    Email: str
    password: str

class GetUserInfo(BaseModel):
    Email: str

class Subscribe(BaseModel):
    user_id: int
    game_id: int

class GameCreate(BaseModel):
    title: str
    rating: float
    platforms: str
    releaseDate: date
    description: str
    genre: str
    user_id: int

class GetDeveloperGames(BaseModel):
    user_id:int

class GameEventCreate(BaseModel):
    game_id: int
    event_type_title: str
    start_time: datetime
    end_time: datetime
    description: str
    rewards: str
    user_id: int

class DeleteEvent(BaseModel):
    event_id: int


class VerifyCode(BaseModel):
    Email: str
    code: str

class ResetPassword(BaseModel):
    email: str
    newPassword: str