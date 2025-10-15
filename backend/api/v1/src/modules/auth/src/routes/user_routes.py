from fastapi import APIRouter, Depends
from src.modules.auth.src.controllers.user_controller import UserController

router = APIRouter()
controller = UserController()

@router.post("/createAccount")
def create_user_with_sub_and_conf(payload: dict):
    result = controller.create_user_with_sub_and_conf(payload)
    return {"message": "Registrazione completata", "result": result}

@router.post("/login")
def login_user(payload: dict):
    session = controller.login_user(payload)
    return {"message": "Login effettuato", "session": session}

@router.get("/getUser/{email}")
def get_user_by_email(email: str):
    return controller.get_user_by_email(email)

@router.post("/magicLink")
def magic_link_login(payload: dict):
    return controller.send_magic_link(payload)

@router.delete("/delete/{user_id}")
def delete_user(user_id: str):
    return controller.delete_account(user_id)

@router.post("/resetPassword")
def reset_password(payload: dict):
    return controller.reset_password(payload)

@router.post("/updatePassword")
def update_password(payload: dict):
    return controller.update_password(payload)

@router.post("/logout")
def logout():
    return controller.logout()