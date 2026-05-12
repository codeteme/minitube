"""Environment-driven settings for the user preferences and accounts service.

Loads values from ``.env`` via ``python-dotenv``. Constants here are shared by
security, database setup, CORS, and request validation.
"""
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
TOKEN_EXPIRES = 30
RESET_TOKEN_EXPIRES = 15
DATABASE_URL = os.getenv("DATABASE_URL")
PASSWORD_MIN_LENGTH = 8

CORS_ALLOW_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://vcm-52418.vm.duke.edu:5173",
    "http://vcm-52527.vm.duke.edu:5173",
]
