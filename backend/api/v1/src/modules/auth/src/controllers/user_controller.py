from src.core.DAO.user_dao import UserDAO

class UserController:
    def __init__(self):
        self.user_dao = UserDAO()

    def create_user_with_sub_and_conf(self, payload: dict):
        email = payload.get("email")
        password = payload.get("password")
        subscription_data = payload.get("subscription")
        configuration_data = payload.get("configuration")

        return self.user_dao.create_user_with_sub_and_conf(email, password, subscription_data, configuration_data)

    def login_user(self, payload: dict):
        email = payload.get("email")
        password = payload.get("password")
        
        return self.user_dao.login_with_password(email, password)
    
    def get_user_by_email(self, email: str):
        return self.user_dao.get_user_by_email(email)

    def send_magic_link(self, payload: dict):
        email = payload.get("email")

        return self.user_dao.login_with_magic_link(email)

    def delete_account(self, user_id: str):
        return self.user_dao.delete_user(user_id)

    def reset_password(self, payload: dict):
        email = payload.get("email")

        return self.user_dao.send_password_reset(email)
    
    def update_password(self, payload: dict):
        new_password = payload.get("new_password")

        return self.user_dao.update_password(new_password)
    
    def logout(self):
        return self.user_dao.logout()
