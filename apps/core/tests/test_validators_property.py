"""
Property-based tests for apps.core.validators.validate_image_file.

**Validates: Requirements 17.2, 17.4**

Property 5 — Upload Validation Rejects All Non-Allowed MIME Types
-----------------------------------------------------------------
For any MIME type string that is NOT in {"image/jpeg", "image/png", "image/webp"},
validate_image_file MUST raise ValidationError, regardless of what bytes are in the
file buffer.  No bytes may reach storage — the error is raised before any write occurs.

Strategy
--------
- Mock `apps.core.validators.magic.from_buffer` to return a MIME string drawn from
  Hypothesis strategies that produce strings outside the allowed set.
- Construct a lightweight file-like mock (supports .read(), .seek(), .size) so the
  validator can execute normally up to the MIME check.
- Assert ValidationError is raised and that the error message names the detected type.
- A companion positive test (not a Hypothesis test) confirms that when the mocked MIME
  is "image/jpeg" and the file is within the size limit, no error is raised.

Note on libmagic
----------------
python-magic requires the `libmagic` C library at import time.  In environments where
it is not installed (e.g. CI without system packages) we inject a stub module into
sys.modules before importing the validator so that the module-level `import magic`
succeeds.  All tests then mock `magic.from_buffer` individually, meaning the stub is
never actually called — the real libmagic path is never exercised and no false
positives arise.
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
# We inject a stub *before* importing the validator module so the top-level
# `import magic` in validators.py succeeds.  Individual tests still patch
# magic.from_buffer explicitly, so the stub's placeholder is never called.
# ---------------------------------------------------------------------------
if "magic" not in sys.modules:
    _magic_stub = types.ModuleType("magic")
    _magic_stub.from_buffer = lambda buf, mime=False: "application/octet-stream"  # placeholder
    sys.modules["magic"] = _magic_stub

from apps.core.validators import ALLOWED_MIME_TYPES, validate_image_file  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_file(content: bytes = b"fake image data", size: int = 1024) -> MagicMock:
    """
    Build a minimal file-like object compatible with validate_image_file.

    The validator calls:
      header = file.read(2048)   → returns bytes
      file.seek(0)               → resets pointer
      mime = magic.from_buffer(header, mime=True)   → mocked
      if file.size > max_bytes   → checked after MIME
    """
    mock_file = MagicMock()
    mock_file.read.return_value = content[:2048]
    mock_file.seek.return_value = None
    mock_file.size = size
    return mock_file


# ---------------------------------------------------------------------------
# Strategy: MIME strings that are NOT in ALLOWED_MIME_TYPES
# ---------------------------------------------------------------------------

# Produce printable text strings that are guaranteed to fall outside the allowed set.
_non_allowed_mime = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pc", "Po")),
    min_size=1,
    max_size=64,
).filter(lambda s: s not in ALLOWED_MIME_TYPES)


# ---------------------------------------------------------------------------
# Property 5 — MIME rejection (Hypothesis)
# ---------------------------------------------------------------------------

@settings(max_examples=20)
@given(mime_type=_non_allowed_mime)
def test_property5_rejects_all_non_allowed_mime_types(mime_type: str) -> None:
    """
    **Validates: Requirements 17.2, 17.4**

    Property 5: For every MIME type not in {image/jpeg, image/png, image/webp},
    validate_image_file raises ValidationError before any storage write occurs.
    """
    mock_file = _make_mock_file()

    with patch("apps.core.validators.magic.from_buffer", return_value=mime_type):
        with pytest.raises(ValidationError) as exc_info:
            validate_image_file(mock_file)

    # The error message must mention the detected MIME type so the user gets
    # a meaningful error (Requirement 17.2).
    # ValidationError stores messages in .messages (a list); join them for
    # the assertion rather than using str() which adds list brackets.
    error_messages = " ".join(exc_info.value.messages)
    assert mime_type in error_messages, (
        f"Expected the ValidationError message to contain '{mime_type}', "
        f"but got: {error_messages}"
    )

    # No bytes should have reached storage — .seek() is called to reset the
    # pointer but .save() or any storage write must never be invoked.
    # The mock records all calls; assert no storage-write methods were called.
    mock_file.write.assert_not_called()


# ---------------------------------------------------------------------------
# Positive test — allowed MIME type must NOT raise
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("allowed_mime", sorted(ALLOWED_MIME_TYPES))
def test_allowed_mime_types_do_not_raise(allowed_mime: str) -> None:
    """
    When magic returns an allowed MIME type and the file is within the size
    limit, validate_image_file must complete without raising ValidationError.

    Companion to Property 5 — confirms the validator only rejects truly
    disallowed types and does not over-reject.
    """
    # 1 KB file, well under any reasonable size limit.
    mock_file = _make_mock_file(content=b"A" * 1024, size=1024)

    with patch("apps.core.validators.magic.from_buffer", return_value=allowed_mime):
        # Should not raise — if it does the test will fail with the exception.
        validate_image_file(mock_file, max_size_mb=5)
