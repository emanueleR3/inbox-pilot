from fastapi import HTTPException
from api.v1.src.modules.auth.src.DAO.user_dao import UserDAO
from  api.v1.src.modules.auth.src.models.subscription_model import Subscription

class UserController:
    def __init__(self, user_dao: UserDAO):
        self.user_dao = user_dao

    def create_user_with_subscription(self, email: str, password: str, subscription):
        if not isinstance(subscription, dict):
            if hasattr(subscription, "model_dump"):
                subscription_data = subscription.model_dump()
            else:
                subscription_data = subscription.dict()
        else:
            subscription_data = subscription

        return self.user_dao.create_user_with_subscription(email, password, subscription_data)

    def login_user(self, email: str, password: str):
        return self.user_dao.login_with_password(email, password)
    
    def get_user_by_email(self, email: str):
        return self.user_dao.get_user_by_email(email)

    def send_magic_link(self, email: str):
        return self.user_dao.login_with_magic_link(email)

    def delete_account(self, user_id: str):
        return self.user_dao.delete_user(user_id)

    def reset_password(self, email: str):
        return self.user_dao.send_password_reset(email)
    
    def update_password(self, new_password: str):
        return self.user_dao.update_password(new_password)
    
    def logout(self):
        return self.user_dao.logout()
