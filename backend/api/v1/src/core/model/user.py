from pydantic import BaseModel, EmailStr
from src.core.model.subscription import SubscriptionRead, Subscription  
from typing import List

class UserCrate(BaseModel):
    email: EmailStr
    password: str

class UserSubscription(BaseModel):
    email: EmailStr
    password: str 
    subscription: Subscription

class UserCrateWithoutPassword(BaseModel):
    email: EmailStr

class UserRead(BaseModel):
    id: str
    email: EmailStr

class UserReadSub(BaseModel):
    id: str
    email: EmailStr
    subscription: SubscriptionRead
    jwt: str

class UserReadSubs(BaseModel):
    id: str
    email: str
    subscriptions: List[SubscriptionRead]  
    jwt: str