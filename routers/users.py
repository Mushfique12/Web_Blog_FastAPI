from datetime import timedelta
from typing import Annotated

import models
from auth import (create_access_token, hash_password, oauth2_scheme,
                  verify_access_token, verify_password)
from config import settings
from database import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from schemas import (PostResponse, Token, UserCreate, UserPrivate, UserPublic,
                     UserUpdate)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# Creates a router for the user endpoints
router = APIRouter()


# API endpoint to create a post, validated using UserCreate Schema
@router.post(
    "", 
    response_model=UserPrivate, 
    status_code=status.HTTP_201_CREATED
)
async def create_user(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    # Finds a matching username in the DB (Query) by converting both to lowercase for case-insensitive comparison
    result = await db.execute(
        select(models.User).where(func.lower(models.User.username) == user.username.lower()),
    )

    # Gets the first user object or None
    existing_user = result.scalars().first()

    # Checks if Username already exists
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    # Finds a matching email in the DB by converting both to lowercase for case-insensitive comparison
    result = await db.execute(
        select(models.User).where(func.lower(models.User.email) == user.email.lower()),
    )

    # Gets the first user object or None
    existing_email = result.scalars().first()

    # Checks if email already exists
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists",
        )

    # Creating a new User
    new_user = models.User(
        username=user.username,
        email=user.email.lower(),
        password_hash=hash_password(user.password)
    )

    # Adding it to the DB
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


# API endpoint to get the current logged-in user, validated using UserPrivate Schema
@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Look up user by email (case-insensitive)
    # Note: OAuth2PasswordRequestForm uses "username" field, but we treat it as email
    result = await db.execute(
        select(models.User).where(
            func.lower(models.User.email) == form_data.username.lower(),
        ),
    )
    user = result.scalars().first()

    # Verify user exists and password is correct
    # Don't reveal which one failed (security best practice)
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token with user id as subject
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
    )
    return Token(access_token=access_token, token_type="bearer")


# API endpoint to get the current logged-in user, validated using UserPrivate Schema
@router.get("/me", response_model=UserPrivate)
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get the currently authenticated user."""
    user_id = verify_access_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate user_id is a valid integer (defense against malformed JWT)
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Query the database for the user with the given ID
    result = await db.execute(
        select(models.User).where(models.User.id == user_id_int),
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# API endpoint to get a specific user by ID, validated using UserResponse Schema
@router.get(
    "/{user_id}",
    response_model=UserPublic
)
async def get_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    # Finds a matching user ID in the DB (Query)
    result = await db.execute(
        select(models.User).where(models.User.id == user_id),
    )

    # Gets the first user object or None
    user = result.scalars().first()

    # Checks if the user exists:
    if user:
        return user

    # Raise an Exception
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found",
    )


# API endpoint to get all posts, by a specific user 
@router.get(
    "/{user_id}/posts",
    response_model=list[PostResponse]
)
async def get_user_posts(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    # Finds a matching user ID in the DB (Query)
    result = await db.execute(
        select(models.User)
        .where(models.User.id == user_id)
    )

    # Gets the first user object or None
    user = result.scalars().first()

    # If user doesn't exist
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Queries all posts by the User
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.user_id == user_id),
    )
    posts = result.scalars().all()
    return posts


# API endpoint to partially update a specific User by ID, validated using PostResponse Schema
@router.patch(
    "/{user_id}",
    response_model=UserPrivate
)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Finds a matching User ID in the DB (Query)
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()

    # If post not found
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Verifying if the New Username already exists
    if user_update.username is not None and user_update.username.lower() != user.username.lower():
        result = await db.execute(
            select(models.User).where(func.lower(models.User.username) == user_update.username.lower()),
        )
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists",
            )

    # Verifying if the New Email already exists
    if user_update.email is not None and user_update.email.lower() != user.email.lower():
        result = await db.execute(
            select(models.User).where(func.lower(models.User.email) == user_update.email.lower()),
        )
        existing_email = result.scalars().first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

    # Updates the info for the user manually
    if user_update.username is not None:
        user.username = user_update.username
    if user_update.email is not None:
        user.email = user_update.email.lower()
    if user_update.image_file is not None:
        user.image_file = user_update.image_file

    # Commiting to the DB
    await db.commit()
    await db.refresh(user)
    return user


# API endpoint to delete a specific User
@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    # Querying the User in the DB
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    await db.delete(user)
    await db.commit()