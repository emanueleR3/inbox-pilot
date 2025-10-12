from fastapi import HTTPException
from api.v1.src.modules.auth.src.DAO.user_dao import UserDAO
from api.v1.src.modules.auth.src.models.user_model import UserCrate

class UserController:
    def __init__(self, user_dao: UserDAO):
        self.user_dao = user_dao

    def create_user(self, email: str, password: str):
        return self.user_dao.create_user(email, password)

    def login_user(self, email: str, password: str):
        return self.user_dao.login_with_password(email, password)

    def send_magic_link(self, email: str):
        return self.user_dao.login_with_magic_link(email)

    def delete_account(self, user_id: str):
        return self.user_dao.delete_user(user_id)

    def reset_password(self, email: str):
        return self.user_dao.send_password_reset(email)
