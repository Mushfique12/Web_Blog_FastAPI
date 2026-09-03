from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
from database import get_db
from schemas import PostResponse, UserCreate, UserResponse, UserUpdate

# Creates a router for the user endpoints
router = APIRouter()


# API endpoint to create a post, validated using UserCreate Schema
@router.post(
    "", 
    response_model=UserResponse, 
    status_code=status.HTTP_201_CREATED
)
async def create_user(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    # Finds a matching username in the DB (Query)
    result = await db.execute(
        select(models.User).where(models.User.username == user.username),
    )

    # Gets the first user object or None
    existing_user = result.scalars().first()

    # Checks if Username already exists
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    # Finds a matching email in the DB
    result = await db.execute(
        select(models.User).where(models.User.email == user.email),
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
        email=user.email,
    )

    # Adding it to the DB
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


# API endpoint to get a specific user by ID, validated using UserResponse Schema
@router.get(
    "/{user_id}",
    response_model=UserResponse
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
    response_model=UserResponse
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
    if user_update.username is not None and user_update.username != user.username:
        result = await db.execute(
            select(models.User).where(models.User.username == user_update.username),
        )
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists",
            )

    # Verifying if the New Email already exists
    if user_update.email is not None and user_update.email != user.email:
        result = await db.execute(
            select(models.User).where(models.User.email == user_update.email),
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
        user.email = user_update.email
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