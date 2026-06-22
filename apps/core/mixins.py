"""
Custom access-control mixins for VIPET.

These mixins enforce role-based access at the view level using Django's
UserPassesTestMixin. Both return HTTP 403 (Forbidden) rather than redirecting
to the login page when the test fails.

Requirements: 16.2, 11.5, 12.4
"""

from django.contrib.auth.mixins import UserPassesTestMixin


class ClientRequiredMixin(UserPassesTestMixin):
    """
    Passes only if request.user.role == 'client'.
    Returns 403 Forbidden otherwise (raise_exception = True).
    """

    raise_exception = True

    def test_func(self) -> bool:
        return (
            self.request.user.is_authenticated
            and self.request.user.role == "client"
        )


class AdminRequiredMixin(UserPassesTestMixin):
    """
    Passes only if request.user.role == 'admin'.
    Returns 403 Forbidden otherwise (raise_exception = True).
    """

    raise_exception = True

    def test_func(self) -> bool:
        return (
            self.request.user.is_authenticated
            and self.request.user.role == "admin"
        )
