"""FastAPI application entrypoint: CORS, routers, and optional admin seeding.

On import, ensures an admin user exists when ``SEED_ADMIN_*`` env vars are set.
Exposes auth, users, preferences, avatars, and system routes under one ASGI app.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.user_prefs_and_accounts_service.avatars import router as avatars_router
from src.user_prefs_and_accounts_service.config import CORS_ALLOW_ORIGINS
from src.user_prefs_and_accounts_service.database import Base, get_db, engine, SessionLocal
from src.user_prefs_and_accounts_service.models import User, UserPreferences
from src.user_prefs_and_accounts_service.schemas import UserResponse
from src.user_prefs_and_accounts_service.dependencies import get_current_active_user, get_current_user
from src.user_prefs_and_accounts_service.routers import auth as auth_router
from src.user_prefs_and_accounts_service.routers import preferences as preferences_router
from src.user_prefs_and_accounts_service.routers import system as system_router
from src.user_prefs_and_accounts_service.routers import users as users_router
from src.user_prefs_and_accounts_service.services.seed import seed_admin_user

app = FastAPI(title="User Accounts Service")
seed_admin_user()

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system_router.router)
app.include_router(auth_router.router)
app.include_router(users_router.router)
app.include_router(preferences_router.router)
app.include_router(avatars_router)

# Re-exports for tests / legacy imports
from src.user_prefs_and_accounts_service.config import ALGORITHM, SECRET_KEY, TOKEN_EXPIRES
from src.user_prefs_and_accounts_service.email_service import send_reset_email
from src.user_prefs_and_accounts_service.schemas import UserResponse, UserUpdate
from src.user_prefs_and_accounts_service.security import (
    create_password_reset_token,
    get_pwd_hash,
)
