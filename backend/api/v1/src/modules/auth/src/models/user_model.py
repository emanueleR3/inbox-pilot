from pydantic import BaseModel, EmailStr

class UserCrate(BaseModel):
    email: EmailStr
    password: str   

class UserCrateWithoutPassword(BaseModel):
    email: EmailStr

class UserRead(BaseModel):
    id: str
    email: EmailStr