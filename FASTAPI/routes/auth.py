from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Mock / shell auth routes. No real logic, hashing, token issuance, or DB
# writes — these exist only as structural contracts matching the frontend's
# expected request/response shapes (Guide 2 Step 5).
router = APIRouter()

_NOT_IMPLEMENTED = {"detail": "Not implemented", "status": "mock"}


class LoginRequest(BaseModel):
    email: str
    password: str


class SignupRequest(BaseModel):
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


@router.post("/api/v1/auth/login")
async def login(payload: LoginRequest):
    return JSONResponse(status_code=501, content=_NOT_IMPLEMENTED)


@router.post("/api/v1/auth/signup")
async def signup(payload: SignupRequest):
    return JSONResponse(status_code=501, content=_NOT_IMPLEMENTED)


@router.post("/api/v1/auth/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest):
    return JSONResponse(status_code=501, content=_NOT_IMPLEMENTED)


@router.get("/api/v1/auth/callback/google")
async def google_callback():
    return JSONResponse(status_code=501, content=_NOT_IMPLEMENTED)


@router.get("/api/v1/auth/callback/github")
async def github_callback():
    return JSONResponse(status_code=501, content=_NOT_IMPLEMENTED)
