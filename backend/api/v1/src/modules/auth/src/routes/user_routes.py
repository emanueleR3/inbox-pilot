from fastapi import APIRouter, Depends
from api.v1.src.modules.auth.src.DAO.user_dao import UserDAO
from api.v1.src.modules.auth.src.controllers.user_controller import UserController
from api.v1.src.modules.auth.src.models.user_model import UserSubscription, UserCrateWithoutPassword, UserCrate
from api.v1.src.core.database import get_supabase_client

router = APIRouter()
@router.post("/createAccount")
def create_user_with_subscription(user: UserSubscription, supabase=Depends(get_supabase_client)):
    controller = UserController(UserDAO(supabase))
    user = controller.create_user_with_subscription(user.email, user.password, user.subscription)
    return {"message": "Registrazione completata", "user": user}

@router.post("/login")
def login_user(user: UserCrate, supabase=Depends(get_supabase_client)):
    controller = UserController(UserDAO(supabase))
    session = controller.login_user(user.email, user.password)
    return {"message": "Login effettuato", "session": session}

@router.get("/get-user/{email}")
def get_user_by_email(email: str, supabase=Depends(get_supabase_client)):
    controller = UserController(UserDAO(supabase))
    return controller.get_user_by_email(email)

@router.post("/magic-link")
def magic_link_login(user: UserCrateWithoutPassword, supabase=Depends(get_supabase_client)):
    controller = UserController(UserDAO(supabase))
    return controller.send_magic_link(user.email)

@router.delete("/delete/{user_id}")
def delete_user(user_id: str, supabase=Depends(get_supabase_client)):
    controller = UserController(UserDAO(supabase))
    return controller.delete_account(user_id)

@router.post("/reset-password")
def reset_password(user: UserCrateWithoutPassword, supabase=Depends(get_supabase_client)):
    controller = UserController(UserDAO(supabase))
    return controller.reset_password(user.email)

@router.post("/update-password")
def update_password(new_password: str, access_token: str, supabase=Depends(get_supabase_client)):
    controller = UserController(UserDAO(supabase))
    return controller.update_password(new_password)

@router.post("/logout")
def logout(supabase=Depends(get_supabase_client)):
    controller = UserController(UserDAO(supabase))
    return controller.logout()