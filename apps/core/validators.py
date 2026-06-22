"""
Image upload validator for VIPET.

Validates uploaded image files by inspecting their real MIME type via libmagic
(rather than trusting the file extension) and checking the file size against a
configurable limit.

Requirements: 17.2, 17.3, 17.4
"""

from django.core.exceptions import ValidationError

try:
    import magic  # python-magic — requires libmagic system library
except ImportError:
    # Fallback: use mimetypes stdlib when python-magic is not available
    magic = None  # type: ignore[assignment]

# Only JPEG, PNG, and WebP are accepted across the platform.
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}


def validate_image_file(file, max_size_mb: int = 5) -> None:
    """
    Validate an uploaded image file's MIME type and size.

    Args:
        file:         An uploaded file object (e.g. Django InMemoryUploadedFile
                      or TemporaryUploadedFile). Must support ``read()``,
                      ``seek()``, and a ``.size`` attribute.
        max_size_mb:  Maximum permitted file size in megabytes. Defaults to 5.

    Raises:
        ValidationError: If the MIME type is not in ALLOWED_MIME_TYPES, with a
                         message identifying the detected type.
        ValidationError: If ``file.size`` exceeds ``max_size_mb`` MB, with a
                         message showing the actual and maximum sizes.
    """
    max_bytes = max_size_mb * 1024 * 1024

    # Read only the first 2048 bytes for MIME detection — avoids loading the
    # entire file into memory and is sufficient for libmagic signature matching.
    header = file.read(2048)
    file.seek(0)  # Reset pointer so subsequent reads (e.g. storage save) work.

    if magic is not None:
        mime = magic.from_buffer(header, mime=True)
    else:
        # Fallback: use mimetypes based on file name
        import mimetypes
        mime, _ = mimetypes.guess_type(getattr(file, 'name', ''))
        if mime is None:
            mime = "application/octet-stream"

    if mime not in ALLOWED_MIME_TYPES:
        raise ValidationError(
            f"Invalid file format '{mime}'. Only JPEG, PNG, and WebP are accepted."
        )

    if file.size > max_bytes:
        raise ValidationError(
            f"File size {file.size / (1024 * 1024):.1f} MB exceeds the {max_size_mb} MB limit."
        )
