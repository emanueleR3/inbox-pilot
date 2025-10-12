from fastapi import APIRouter, Depends
from api.v1.src.modules.auth.src.DAO.user_dao import UserDAO
from api.v1.src.modules.auth.src.controllers.user_controller import UserController
from api.v1.src.modules.auth.src.models.user_model import UserCrate, UserCrateWithoutPassword
from api.v1.src.core.database import get_supabase_client

router = APIRouter()
@router.post("/createAccount")
async def create_user(user: UserCrate, supabase=Depends(get_supabase_client)):
    controller = UserController(UserDAO(supabase))
    user = controller.create_user(user.email, user.password)
    return {"message": "Registrazione completata", "user": user}

@router.post("/login")
async def login_user(user: UserCrate, supabase=Depends(get_supabase_client)):
    controller = UserController(UserDAO(supabase))
    session = controller.login_user(user.email, user.password)
    return {"message": "Login effettuato", "session": session}

@router.post("/magic-link")
async def magic_link_login(user: UserCrateWithoutPassword, supabase=Depends(get_supabase_client)):
    controller = UserController(UserDAO(supabase))
    return controller.send_magic_link(user.email)

@router.delete("/delete/{user_id}")
async def delete_user(user_id: str, supabase=Depends(get_supabase_client)):
    controller = UserController(UserDAO(supabase))
    return controller.delete_account(user_id)

@router.post("/reset-password")
async def reset_password(user: UserCrateWithoutPassword, supabase=Depends(get_supabase_client)):
    controller = UserController(UserDAO(supabase))
    return controller.reset_password(user.email)
