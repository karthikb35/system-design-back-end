"""Users HTTP endpoints — thin routing layer.

Each handler: (1) receives validated Pydantic input, (2) builds the service with
a request-scoped repository, (3) delegates, and (4) maps domain exceptions to
HTTP status codes. No business logic or SQL lives here.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..dependencies import get_current_user_id
from ..repository import UserRepository
from ..schemas import LoginRequest, TokenResponse, UserCreate, UserOut
from ..service import EmailAlreadyExists, InvalidCredentials, UserService

router = APIRouter(prefix="/users", tags=["users"])


def _service(session: AsyncSession = Depends(get_session)) -> UserService:
    """Assemble the service graph for one request (dependency injection)."""
    return UserService(UserRepository(session))


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, svc: UserService = Depends(_service)) -> UserOut:
    try:
        user = await svc.register(payload)
    except EmailAlreadyExists:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="email already registered")
    return UserOut.model_validate(user)


@router.get("/me", response_model=UserOut)
async def read_current_user(
    user_id: str = Depends(get_current_user_id),
    svc: UserService = Depends(_service),
) -> UserOut:
    """Return the caller's own record, resolved from the token's subject.

    Declared BEFORE `/{user_id}` so the literal path "me" is matched here rather
    than being captured as a user id by the parametrised route below.
    """
    user = await svc.get(user_id)
    if user is None:
        # The token verified but its subject no longer exists (e.g. deleted).
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="user not found")
    return UserOut.model_validate(user)


@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: str, svc: UserService = Depends(_service)) -> UserOut:
    user = await svc.get(user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="user not found")
    return UserOut.model_validate(user)


@router.get("", response_model=list[UserOut])
async def list_users(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _caller_id: str = Depends(get_current_user_id),
    svc: UserService = Depends(_service),
) -> list[UserOut]:
    # Listing the whole roster is privileged, so this route requires a valid
    # Bearer token; create_user and login stay public so a new user can still
    # register and obtain one. Enforcement lives in the users service because it
    # is the token issuer and holds the signing secret.
    users = await svc.list(limit=limit, offset=offset)
    return [UserOut.model_validate(u) for u in users]


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, svc: UserService = Depends(_service)) -> TokenResponse:
    try:
        token = await svc.authenticate(payload.email, payload.password)
    except InvalidCredentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    return TokenResponse(access_token=token)
