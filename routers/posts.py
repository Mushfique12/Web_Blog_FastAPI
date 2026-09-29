from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
from auth import CurrentUser
from database import get_db
from schemas import PostCreate, PostResponse, PostUpdate

# Creates a router for the post endpoints
router = APIRouter()


# API endpoint to get all posts, validated using PostResponse Schema
@router.get(
    "",
    response_model=list[PostResponse]
)
async def get_posts(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .order_by(models.Post.date_posted.desc()),
    )
    posts = result.scalars().all()
    return posts


# API endpoint to create a post, validated using PostCreate Schema
@router.post(
    "",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_post(
    post: PostCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    # Creates the post with the authenticated user ID using DB models
    new_post = models.Post(
        title=post.title,
        content=post.content,
        user_id=current_user.id,
    )

    # Add it to the DB
    db.add(new_post)
    await db.commit()
    # Refresh the post to get the author relationship loaded
    await db.refresh(new_post, attribute_names=["author"])
    return new_post


# API endpoint to get a specific post by ID, validated using PostResponse Schema
@router.get(
    "/{post_id}",
    response_model=PostResponse
)
async def get_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    # Finds a matching post ID in the DB (Query)
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id)
    )
    post = result.scalars().first()

    if post:
        return post

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


# API endpoint to fully update a specific post by ID, validated using PostResponse Schema
@router.put(
    "/{post_id}",
    response_model=PostResponse
)
async def update_post_full(
    post_id: int,
    post_data: PostCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    # Finds a matching post ID in the DB (Query)
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()

    # If post not found
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    # Checks if the current user is the author of the post
    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this post"
        )

    # Updates the info for the post
    post.title = post_data.title
    post.content = post_data.content

    # Commiting to the DB
    await db.commit()
    # Refresh the post to get the author relationship loaded
    await db.refresh(post, attribute_names=["author"])
    return post


# API endpoint to partially update a specific post by ID, validated using PostResponse Schema
@router.patch(
    "/{post_id}",
    response_model=PostResponse
)
async def update_post_partial(
    post_id: int,
    post_data: PostUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Finds a matching post ID in the DB (Query)
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()

    # If post not found
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    # Checks if the current user is the author of the post
    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this post"
        )

    # Updates the info for the post
    # Only gets what the client actually sent (otherwise, the missing fields would be set to default)
    update_data = post_data.model_dump(exclude_unset=True)
    # Dynamically sets each provided field on the post object
    for field, value in update_data.items():
        setattr(post, field, value)

    # Commiting to the DB
    await db.commit()
    # Refresh the post to get the author relationship loaded
    await db.refresh(post, attribute_names=["author"])
    return post


# API endpoint to delete a specific post by ID, validated using PostResponse Schema
@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_post(
    post_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    # Finds a matching post ID in the DB (Query)
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()

    # If post not found
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    # Checks if the current user is the author of the post
    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this post"
        )

    # Deleting from the DB
    await db.delete(post)
    await db.commit()