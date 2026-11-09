from pydantic import BaseModel,EmailStr
from typing import Optional
from enum import Enum
from config import USER_ID



class userCreate(BaseModel):
    name : str
    email : EmailStr

class userResponse(BaseModel):
    user_id : str
    name : str
    email : EmailStr

class LanguageCode(str,Enum):
    english = "en"
    hindi = "hi"
    spanish = "es"

class videoCreate(BaseModel):
      user_id : str = USER_ID
      video_url : str
      lang : list[LanguageCode]


class videoResponse(BaseModel):
    video_id : str
    user_id : str
    video_url : str
    lang : list[LanguageCode]

class questionCreate(BaseModel):
    video_id : str
    question : str

class questionResponse(BaseModel):
    question_id : str
    video_id : str
    question : str
    answer : Optional[str] = None

