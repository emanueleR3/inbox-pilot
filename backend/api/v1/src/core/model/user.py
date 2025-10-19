from pydantic import BaseModel, EmailStr

# TODO, passare il payload e poi il DAO si preoccupa di convertirlo in model
from src.core.model.subscription import SubscriptionRead, Subscription  
from src.core.model.subscription_service import SubscriptionServiceRead

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

class UserReadSubConf(BaseModel):
    id: str
    email: EmailStr
    subscription: SubscriptionRead
    configuration: SubscriptionServiceRead