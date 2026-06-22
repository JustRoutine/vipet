"""
Property-based tests for apps.core.validators.validate_image_file — size checking.

**Validates: Requirements 17.3, 17.4**

Property 6 — Upload Validation Rejects Files Exceeding Size Limit
-----------------------------------------------------------------
For any file whose .size attribute strictly exceeds max_size_mb * 1024 * 1024 bytes,
validate_image_file MUST raise ValidationError with a message that reports the actual
size (in MB) and the configured limit.  No bytes may reach storage — the error is
raised before any write can occur.

Strategy
--------
- Mock `apps.core.validators.magic.from_buffer` to return "image/jpeg" so the MIME
  check always passes.  This isolates the size check as the sole code path under test.
- Use st.integers(min_value=1) to generate excess bytes above the limit, then set
  file.size = max_bytes + excess so the file is always over-limit.
- Also test boundary behaviour explicitly:
    * file.size == max_bytes       → must NOT raise (equal is within limit)
    * file.size == max_bytes + 1   → MUST raise

Note on libmagic
----------------
python-magic requires the `libmagic` C library at import time.  In CI environments
where libmagic is absent we inject a stub module into sys.modules before importing the
validator, exactly as in test_validators_property.py.  All tests then patch
magic.from_buffer explicitly so the stub placeholder is never reached.
"""

import sys
import types
from unittest.mock import MagicMock, patch

import pytest
from django.core.exceptions import ValidationError
from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Ensure python-magic can be imported even when libmagic is absent.
# Inject a stub *before* importing the validator so the top-level
# `import magic` in validators.py succeeds without the C library.
# ---------------------------------------------------------------------------
if "magic" not in sys.modules:
    _magic_stub = types.ModuleType("magic")
    _magic_stub.from_buffer = lambda buf, mime=False: "application/octet-stream"
    sys.modules["magic"] = _magic_stub

from apps.core.validators import validate_image_file  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ALLOWED_MIME = "image/jpeg"  # used in every mock so only size is tested


def _make_mock_file(size: int, content: bytes = b"fake image data") -> MagicMock:
    """
    Build a minimal file-like object compatible with validate_image_file.

    validate_image_file calls:
      header = file.read(2048)    — returns bytes header
      file.seek(0)                — resets pointer
      mime = magic.from_buffer(…) — mocked to return an allowed type
      if file.size > max_bytes    — uses .size attribute for size check
    """
    mock_file = MagicMock()
    mock_file.read.return_value = content[:2048]
    mock_file.seek.return_value = None
    mock_file.size = size
    return mock_file


# ---------------------------------------------------------------------------
# Property 6 — size rejection (Hypothesis)
# ---------------------------------------------------------------------------

@settings(max_examples=20)
@given(
    max_size_mb=st.integers(min_value=1, max_value=50),
    excess_bytes=st.integers(min_value=1, max_value=100 * 1024 * 1024),  # 1 byte to 100 MB over
)
def test_property6_rejects_files_exceeding_size_limit(
    max_size_mb: int, excess_bytes: int
) -> None:
    """
    **Validates: Requirements 17.3, 17.4**

    Property 6: For any file whose .size strictly exceeds max_size_mb * 1024 * 1024,
    validate_image_file raises ValidationError (even when MIME type is allowed).
    """
    max_bytes = max_size_mb * 1024 * 1024
    oversized = max_bytes + excess_bytes

    mock_file = _make_mock_file(size=oversized)

    with patch("apps.core.validators.magic.from_buffer", return_value=_ALLOWED_MIME):
        with pytest.raises(ValidationError) as exc_info:
            validate_image_file(mock_file, max_size_mb=max_size_mb)

    # Error message must report both the actual size and the limit so the user
    # understands why the upload was rejected (Requirement 17.3).
    error_messages = " ".join(exc_info.value.messages)

    actual_mb = f"{oversized / (1024 * 1024):.1f}"
    assert actual_mb in error_messages, (
        f"Expected error message to contain actual size '{actual_mb} MB', "
        f"but got: {error_messages}"
    )
    assert str(max_size_mb) in error_messages, (
        f"Expected error message to contain the limit '{max_size_mb}', "
        f"but got: {error_messages}"
    )

    # No storage writes must have occurred — the error is raised before any
    # write path is reached (Requirement 17.4).
    mock_file.write.assert_not_called()


# ---------------------------------------------------------------------------
# Boundary tests — exact limit should pass; one byte over must fail
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("max_size_mb", [1, 5, 10])
def test_file_exactly_at_limit_does_not_raise(max_size_mb: int) -> None:
    """
    A file whose .size equals the exact byte limit must NOT raise ValidationError.
    The boundary is inclusive: size == max_bytes is within limit.

    **Validates: Requirements 17.3**
    """
    max_bytes = max_size_mb * 1024 * 1024
    mock_file = _make_mock_file(size=max_bytes)

    with patch("apps.core.validators.magic.from_buffer", return_value=_ALLOWED_MIME):
        # Should complete without raising.
        validate_image_file(mock_file, max_size_mb=max_size_mb)


@pytest.mark.parametrize("max_size_mb", [1, 5, 10])
def test_file_one_byte_over_limit_raises(max_size_mb: int) -> None:
    """
    A file whose .size is exactly one byte over the limit MUST raise ValidationError.

    **Validates: Requirements 17.3, 17.4**
    """
    max_bytes = max_size_mb * 1024 * 1024
    mock_file = _make_mock_file(size=max_bytes + 1)

    with patch("apps.core.validators.magic.from_buffer", return_value=_ALLOWED_MIME):
        with pytest.raises(ValidationError) as exc_info:
            validate_image_file(mock_file, max_size_mb=max_size_mb)

    error_messages = " ".join(exc_info.value.messages)
    assert str(max_size_mb) in error_messages, (
        f"Expected the size limit ({max_size_mb} MB) in the error message, "
        f"but got: {error_messages}"
    )
    mock_file.write.assert_not_called()


# ---------------------------------------------------------------------------
# Positive test — within-limit file with allowed MIME must never raise
# ---------------------------------------------------------------------------

@settings(max_examples=20)
@given(
    max_size_mb=st.integers(min_value=1, max_value=50),
    deficit_bytes=st.integers(min_value=1, max_value=1024 * 1024),  # at least 1 byte under
)
def test_within_limit_file_does_not_raise(max_size_mb: int, deficit_bytes: int) -> None:
    """
    When the MIME type is allowed and the file size is strictly below the limit,
    validate_image_file must complete without raising any exception.

    Companion to Property 6 — guards against over-rejection.

    **Validates: Requirements 17.3**
    """
    max_bytes = max_size_mb * 1024 * 1024
    # Ensure size is at least 0 (can't be negative).
    file_size = max(0, max_bytes - deficit_bytes)

    mock_file = _make_mock_file(size=file_size)

    with patch("apps.core.validators.magic.from_buffer", return_value=_ALLOWED_MIME):
        # Must not raise.
        validate_image_file(mock_file, max_size_mb=max_size_mb)
