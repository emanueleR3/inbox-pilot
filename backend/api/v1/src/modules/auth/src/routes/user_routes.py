from fastapi import APIRouter, Depends
from src.modules.auth.src.DAO.user_dao import UserDAO
from src.modules.auth.src.controllers.user_controller import UserController
from src.modules.auth.src.models.user_model import UserSubscription, UserCrateWithoutPassword, UserCrate
from src.core.database import get_supabase_client


router = APIRouter()
supabase_client = get_supabase_client()

@router.post("/createAccount")
def create_user_with_subscription(user: UserSubscription):
    controller = UserController(UserDAO(supabase_client))
    user = controller.create_user_with_subscription(user.email, user.password, user.subscription)
    return {"message": "Registrazione completata", "user": user}

@router.post("/login")
def login_user(user: UserCrate):
    controller = UserController(UserDAO(supabase_client))
    session = controller.login_user(user.email, user.password)
    return {"message": "Login effettuato", "session": session}

@router.get("/getUser/{email}")
def get_user_by_email(email: str):
    controller = UserController(UserDAO(supabase_client))
    return controller.get_user_by_email(email)

@router.post("/magicLink")
def magic_link_login(user: UserCrateWithoutPassword):
    controller = UserController(UserDAO(supabase_client))
    return controller.send_magic_link(user.email)

@router.delete("/delete/{user_id}")
def delete_user(user_id: str):
    controller = UserController(UserDAO(supabase_client))
    return controller.delete_account(user_id)

@router.post("/resetPassword")
def reset_password(user: UserCrateWithoutPassword):
    controller = UserController(UserDAO(supabase_client))
    return controller.reset_password(user.email)

@router.post("/updatePassword")
def update_password(new_password: str, access_token: str):
    controller = UserController(UserDAO(supabase_client))
    return controller.update_password(new_password)

@router.post("/logout")
def logout():
    controller = UserController(UserDAO(supabase_client))
    return controller.logout()