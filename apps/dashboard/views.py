"""
Dashboard views for the VIPET platform.

ClientDashboardView: Pet count + recent reservations for clients.
AdminDashboardView: KPIs + management overview for administrators.
AdminUserListView: Paginated user list for admin management.
AdminPetListView: Paginated pet list for admin management.

Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7, 14.8, 15.1–15.5
"""

from django.db.models import Count, Sum
from django.utils import timezone
from django.views.generic import ListView, TemplateView

from apps.accounts.models import CustomUser
from apps.core.mixins import AdminRequiredMixin, ClientRequiredMixin
from apps.pets.models import Pet
from apps.reservations.models import Reservation
from apps.services.models import Service


# ---------------------------------------------------------------------------
# Client Dashboard
# ---------------------------------------------------------------------------


class ClientDashboardView(ClientRequiredMixin, TemplateView):
    """
    Client dashboard displaying pet count and 5 most recent reservations.

    Access:
      - Authenticated clients only (ClientRequiredMixin).
      - Admins receive HTTP 403.
      - Unauthenticated users receive HTTP 403 (handled by mixin).

    Context:
      - pet_count: number of pets owned by the authenticated client.
      - recent_reservations: 5 most recent reservations for the client,
        ordered by creation date descending.

    Requirements: 15.1, 15.2, 15.3, 15.4, 15.5
    """

    template_name = "dashboard/client_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context["pet_count"] = Pet.objects.filter(owner=user).count()
        context["recent_reservations"] = (
            Reservation.objects.filter(client=user)
            .select_related("pet", "service")
            .order_by("-created_at")[:5]
        )

        return context


class LiveCameraView(ClientRequiredMixin, TemplateView):
    """
    Live camera page for clients to watch their pets during active stays.

    Context:
      - active_reservations: Reservations with status "approved" for the
        current client, ordered by start_date ascending.
    """

    template_name = "dashboard/live_camera.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.now().date()

        context["active_reservations"] = (
            Reservation.objects.filter(
                client=user,
                status="approved",
                start_date__lte=today,
                end_date__gte=today,
            )
            .select_related("pet", "service")
            .order_by("start_date")
        )

        return context


# ---------------------------------------------------------------------------
# Admin Dashboard
# ---------------------------------------------------------------------------


class AdminDashboardView(AdminRequiredMixin, TemplateView):
    """
    Admin dashboard displaying KPIs and management overview.

    KPIs:
      - total_users: Total registered users
      - total_pets: Total registered pets
      - active_reservations: Count of reservations with status pending or approved
      - monthly_revenue: Sum of service prices for completed reservations this month
      - most_requested_service: Service with highest reservation count
        (alphabetical tiebreaker)

    Requirements: 14.1, 14.5, 14.6, 14.7, 14.8
    """

    template_name = "dashboard/admin_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # KPI: Total users
        context["total_users"] = CustomUser.objects.count()

        # KPI: Total pets
        context["total_pets"] = Pet.objects.count()

        # KPI: Active reservations (pending or approved)
        context["active_reservations"] = Reservation.objects.filter(
            status__in=["pending", "approved"]
        ).count()

        # KPI: Monthly revenue — sum of service prices for completed reservations
        # whose end_date falls within the current calendar month
        now = timezone.now()
        first_day_of_month = now.replace(day=1).date()
        if now.month == 12:
            last_day_of_month = now.replace(
                year=now.year + 1, month=1, day=1
            ).date()
        else:
            last_day_of_month = now.replace(
                month=now.month + 1, day=1
            ).date()

        monthly_revenue = Reservation.objects.filter(
            status="completed",
            end_date__gte=first_day_of_month,
            end_date__lt=last_day_of_month,
        ).aggregate(total=Sum("service__price"))["total"]
        context["monthly_revenue"] = monthly_revenue if monthly_revenue else 0

        # KPI: Most requested service (highest reservation count, alphabetical tiebreaker)
        most_requested = (
            Service.objects.annotate(reservation_count=Count("reservations"))
            .filter(reservation_count__gt=0)
            .order_by("-reservation_count", "name")
            .first()
        )
        context["most_requested_service"] = (
            most_requested.name if most_requested else "N/A"
        )

        return context


class AdminUserListView(AdminRequiredMixin, ListView):
    """
    Paginated list of all users for admin management.

    Sorted by date joined descending, showing email, full name, role,
    and date joined. 20 items per page.

    Requirements: 14.2
    """

    model = CustomUser
    template_name = "dashboard/admin_user_list.html"
    context_object_name = "users"
    paginate_by = 20
    ordering = ["-date_joined"]


class AdminPetListView(AdminRequiredMixin, ListView):
    """
    Paginated list of all pets for admin management.

    Sorted by creation date descending, showing name, species, owner email,
    and creation date. 20 items per page.

    Requirements: 14.3
    """

    model = Pet
    template_name = "dashboard/admin_pet_list.html"
    context_object_name = "pets"
    paginate_by = 20

    def get_queryset(self):
        return Pet.objects.select_related("owner").order_by("-created_at")
