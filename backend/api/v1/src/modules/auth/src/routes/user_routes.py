from fastapi import APIRouter, Depends
from src.core.DAO.user_dao import UserDAO
from src.modules.auth.src.controllers.user_controller import UserController
from src.modules.auth.src.models.user_model import UserSubscription, UserCrateWithoutPassword, UserCrate

router = APIRouter()
controller = UserController()

@router.post("/createAccount")
def create_user_with_subscription(user: UserSubscription):
    user = controller.create_user_with_subscription(user.email, user.password, user.subscription)
    return {"message": "Registrazione completata", "user": user}

@router.post("/login")
def login_user(user: UserCrate):
    session = controller.login_user(user.email, user.password)
    return {"message": "Login effettuato", "session": session}

@router.get("/getUser/{email}")
def get_user_by_email(email: str):
    return controller.get_user_by_email(email)

@router.post("/magicLink")
def magic_link_login(user: UserCrateWithoutPassword):
    return controller.send_magic_link(user.email)

@router.delete("/delete/{user_id}")
def delete_user(user_id: str):
    return controller.delete_account(user_id)

@router.post("/resetPassword")
def reset_password(user: UserCrateWithoutPassword):
    return controller.reset_password(user.email)

@router.post("/updatePassword")
def update_password(new_password: str, access_token: str):
    return controller.update_password(new_password)

@router.post("/logout")
def logout():
    return controller.logout()