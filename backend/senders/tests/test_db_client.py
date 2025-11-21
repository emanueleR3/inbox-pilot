"""
Test for db_client: retrieve user email from box_email.
"""
import os
import sys

# Ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.db_client import get_user_email_from_box_email

def test_get_user_email_from_box_email():
    box_email = "INSERT_TEST_BOX_EMAIL_HERE"
    user_email = get_user_email_from_box_email(box_email)
    print(f"\n[TEST] Box email: {box_email}")
    print(f"[TEST] User email from auth: {user_email}")
    assert user_email is None or isinstance(user_email, str)

if __name__ == "__main__":
    test_get_user_email_from_box_email()
