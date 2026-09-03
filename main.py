from typing import Annotated
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
from database import Base, engine, get_db
from schemas import PostCreate, PostResponse, PostUpdate, UserCreate, UserResponse, UserUpdate


# Creates the Database tables
@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup 
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()


# Create FastAPI application instance
app = FastAPI(lifespan=lifespan)
# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")
# Mount media directory for user uploaded content
app.mount("/media", StaticFiles(directory="media"), name="media")
# Set up Jinja2 templates
templates = Jinja2Templates(directory="templates")


# Define routes for the FastAPI application
@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
async def home(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
    # Queries DB for all posts
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
    )
    posts = result.scalars().all()

    # Returns the HTML template with all the posts
    return templates.TemplateResponse(
        request, 
        "home.html", 
        {"posts": posts, "title": "Home"},
    )


# Define route to get a specific post by ID
@app.get("/posts/{post_id}", include_in_schema=False)
async def post_page(request: Request, post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    # Queries DB for the post with the matching ID
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id)
    )
    post = result.scalars().first()

    # If post exists
    if post:
        title = post.title[:50]
        return templates.TemplateResponse(
            request,
            "post.html",
            {"post": post, "title": title},
        )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


# Define route to get all posts, by a specific user 
@app.get("/users/{user_id}/posts", include_in_schema=False, name="user_posts")
async def user_posts_page(
    request: Request,
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Queries DB for the post with the matching ID
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()

   # If user doesnt exist
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

    return templates.TemplateResponse(
        request,
        "user_posts.html",
        {"posts": posts, "user": user, "title": f"{user.username}'s Posts"},
    )


# API endpoint to create a post, validated using UserCreate Schema
@app.post("/api/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
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
@app.get("/api/user/{user_id}", response_model=UserResponse)
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
@app.get("/api/users/{user_id}/posts", response_model=list[PostResponse])
async def get_user_posts(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    # Finds a matching user ID in the DB (Query)
    result = await db.execute(select(models.User).where(models.User.id == user_id))

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
@app.patch("/api/users/{user_id}", response_model=UserResponse)
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
@app.delete("/api/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
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


# API endpoint to get all posts, validated using PostResponse Schema
@app.get("/api/posts", response_model=list[PostResponse])
async def get_posts(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.Post).options(selectinload(models.Post.author)),
    )
    posts = result.scalars().all()
    return posts


# API endpoint to create a post, validated using PostCreate Schema
@app.post("/api/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(post: PostCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    # Queries DB for the user ID
    result = await db.execute(select(models.User).where(models.User.id == post.user_id))
    user = result.scalars().first()

    # Checks if User exists
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Creates the post with the user ID
    new_post = models.Post(
        title=post.title,
        content=post.content,
        user_id=post.user_id,
    )

    # Add it to the DB
    db.add(new_post)
    await db.commit()
    await db.refresh(new_post, attribute_names=["author"])
    return new_post


# API endpoint to get a specific post by ID, validated using PostResponse Schema
@app.get("/api/posts/{post_id}", response_model=PostResponse)
async def get_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    # Finds a matching post ID in the DB (Query)
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()

    if post:
        return post

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


# API endpoint to fully update a specific post by ID, validated using PostResponse Schema
@app.put("/api/posts/{post_id}", response_model=PostResponse)
async def update_post_full(post_id: int, 
                     post_data: PostCreate, 
                     db: Annotated[AsyncSession, Depends(get_db)]):
    # Finds a matching post ID in the DB (Query)
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()

    # If post not found
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    # If the current user is different than the original
    if post_data.user_id != post.user_id:
        # Checks if the current user exists in the DB
        result = await db.execute(
            select(models.User).where(models.User.id == post_data.user_id),
        )
        user = result.scalars().first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

    # Updates the info for the post
    post.title = post_data.title
    post.content = post_data.content
    post.user_id = post_data.user_id

    # Commiting to the DB
    await db.commit()
    await db.refresh(post, attribute_names=["author"])
    return post


# API endpoint to partially update a specific post by ID, validated using PostResponse Schema
@app.patch("/api/posts/{post_id}", response_model=PostResponse)
async def update_post_partial(
    post_id: int,
    post_data: PostUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Finds a matching post ID in the DB (Query)
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()

    # If post not found
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


    # Updates the info for the post
    # Only gets what the client actually sent (otherwise, the missing fields would be set to default)
    update_data = post_data.model_dump(exclude_unset=True)
    # Dynamically sets each provided field on the post object
    for field, value in update_data.items():
        setattr(post, field, value)

    # Commiting to the DB
    await db.commit()
    await db.refresh(post, attribute_names=["author"])
    return post


# API endpoint to delete a specific post by ID, validated using PostResponse Schema
@app.delete("/api/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    # Finds a matching post ID in the DB (Query)
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()

    # If post not found
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    # Deleting from the DB
    await db.delete(post)
    await db.commit()


# Custom exception handler for validation errors
@app.exception_handler(StarletteHTTPException)
async def general_http_exception_handler(
    request: Request, exception: StarletteHTTPException
):
    # Return JSON response for API requests, otherwise render error template
    if request.url.path.startswith("/api"):
        return await http_exception_handler(request, exception)

    message = (
        exception.detail
        if exception.detail
        else "An error occurred. Please check your request and try again."
    )

    # Render error template for non-API requests
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": exception.status_code,
            "title": exception.status_code,
            "message": message,
        },
        status_code=exception.status_code,
    )

# Custom exception handler for request validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exception: RequestValidationError):
    # Return JSON response for API requests, otherwise render error template
    if request.url.path.startswith("/api"):
        return await request_validation_exception_handler(request, exception)

    # Render error template for non-API requests
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": "Invalid request. Please check your input and try again.",
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )