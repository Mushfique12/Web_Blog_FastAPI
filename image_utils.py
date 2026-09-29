import uuid  # Generate unique filenames for uploaded images
from io import BytesIO  # Work with image bytes in memmory
from pathlib import Path  # Work with file paths

from PIL import Image, ImageOps  # Image processing and manipulation

PROFILE_PICS_DIR = Path("media/profile_pics")


def process_profile_image(content: bytes) -> str:
    with Image.open(BytesIO(content)) as original:
        # Correct the orientation of the image based on EXIF data
        img = ImageOps.exif_transpose(original)
        # Resize and crop the image to fit within a 300x300 square while maintaining aspect ratio
        img = ImageOps.fit(img, (300, 300), method=Image.Resampling.LANCZOS)
        
        # Convert the image to RGB mode if it has an alpha channel or is in a palette mode
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")

        # Generate a unique filename for the processed image and save it to the profile pictures directory
        filename = f"{uuid.uuid4().hex}.jpg"
        filepath = PROFILE_PICS_DIR / filename

        # Create the profile pictures directory if it doesn't exist
        PROFILE_PICS_DIR.mkdir(parents=True, exist_ok=True)

        img.save(filepath, "JPEG", quality=85, optimize=True)

    return filename


def delete_profile_image(filename: str | None) -> None:
    if filename is None:
        return

    filepath = PROFILE_PICS_DIR / filename
    if filepath.exists():
        # Delete the profile image file from the filesystem
        filepath.unlink()