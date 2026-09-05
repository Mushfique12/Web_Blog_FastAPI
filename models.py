# Needed for older Python versions for forward referencing
from __future__ import annotations

from datetime import UTC, datetime

from database import Base
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship


# Creates a Table named - "users"
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    image_file: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        default=None,
    )

    # One-to-Many relationship - One user can have multiple posts
    # Python 3.14+ allows forward reference (ref sth before its actually defined)
    # Cascade - Deletes posts if the user is deleted
    posts: Mapped[list[Post]] = relationship(back_populates="author",
                                cascade="all, delete-orphan")

    @property
    def image_path(self) -> str:
        # If the user has an uploaded custom image
        if self.image_file:
            return f"/media/profile_pics/{self.image_file}"
        # Else return the Default Profile Pic
        return "/static/profile_pics/default.jpg"


# Creates a Table named - "posts"
class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    date_posted: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    # Many-to-one relationship - each Post only has 1 author
    author: Mapped[User] = relationship(back_populates="posts")