from typing import Annotated
from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

import models
from database import Base, engine, get_db
from schemas import PostCreate, PostResponse, UserCreate, UserResponse

# Creates the Database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI application instance
app = FastAPI()
# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")
# Mount media directory for user uploaded content
app.mount("/media", StaticFiles(directory="media"), name="media")
# Set up Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Define routes for the FastAPI application
@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
def home(request: Request, db: Annotated[Session, Depends(get_db)]):
    # Queries DB for all posts
    result = db.execute(select(models.Post))
    posts = result.scalars().all()

    # Returns the HTML template with all the posts
    return templates.TemplateResponse(
            request, 
            "home.html", 
            {"posts": posts, "title": "Home"},
            )

# Define route to get a specific post by ID
@app.get("/posts/{post_id}", include_in_schema=False)
def post_page(request: Request, post_id: int, db: Annotated[Session, Depends(get_db)]):
    # Queries DB for the post with the matching ID
    result = db.execute(select(models.Post).where(models.Post.id == post_id))
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
def user_posts_page(
    request: Request,
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    # Queries DB for the post with the matching ID
    result = db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()

   # If user doesnt exist
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Queries all posts by the User
    result = db.execute(select(models.Post).where(models.Post.user_id == user_id))
    posts = result.scalars().all()

    return templates.TemplateResponse(
        request,
        "user_posts.html",
        {"posts": posts, "user": user, "title": f"{user.username}'s Posts"},
    )


# API endpoint to create a post, validated using PostCreate Schema
@app.post("/api/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Annotated[Session, Depends(get_db)]):
    # Finds a matching username in the DB (Query)
    result = db.execute(
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
    result = db.execute(
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
    db.commit()
    db.refresh(new_user)

    return new_user

# API endpoint to get a specific user by ID, validated using PostResponse Schema
@app.get("/api/user/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Annotated[Session, Depends(get_db)]):
    # Finds a matching user ID in the DB (Query)
    result = db.execute(
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
def get_user_posts(user_id: int, db: Annotated[Session, Depends(get_db)]):
    # Finds a matching user ID in the DB (Query)
    result = db.execute(select(models.User).where(models.User.id == user_id))

    # Gets the first user object or None
    user = result.scalars().first()

    # If user doesn't exist
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Queries all posts by the User
    result = db.execute(select(models.Post).where(models.Post.user_id == user_id))
    posts = result.scalars().all()
    return posts

# API endpoint to get all posts, validated using PostResponse Schema
@app.get("/api/posts", response_model=list[PostResponse])
def get_posts(db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.Post))
    posts = result.scalars().all()
    return posts

# API endpoint to get a specific post by ID, validated using PostResponse Schema
@app.get("/api/posts/{post_id}", response_model=PostResponse)
def get_post(post_id: int, db: Annotated[Session, Depends(get_db)]):
    # Finds a matching post ID in the DB (Query)
    result = db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()

    if post:
        return post

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

# API endpoint to create a post, validated using PostCreate Schema
@app.post("/api/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(post: PostCreate, db: Annotated[Session, Depends(get_db)]):
    # Queries DB for the user ID
    result = db.execute(select(models.User).where(models.User.id == post.user_id))
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
    db.commit()
    db.refresh(new_post)
    return new_post

# Custom exception handler for validation errors
@app.exception_handler(StarletteHTTPException)
def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
    message = (
        exception.detail
        if exception.detail
        else "An error occurred. Please check your request and try again."
    )

    # Return JSON response for API requests, otherwise render error template
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=exception.status_code,
            content={"detail": message},
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
def validation_exception_handler(request: Request, exception: RequestValidationError):
    # Return JSON response for API requests, otherwise render error template
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": exception.errors()},
        )

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