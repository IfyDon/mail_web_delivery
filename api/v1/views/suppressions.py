"""API views for suppression-list management.

GET  /api/v1/suppressions/          - list suppressions (?type=bounce|complaint|unsubscribe &email=)
POST /api/v1/suppressions/          - manually add an email
DELETE /api/v1/suppressions/        - bulk remove emails  (body: {emails: [...]})
DELETE /api/v1/suppressions/<email>/ - remove a single email
GET  /api/v1/suppressions/export/   - download all suppressions as CSV
"""
import csv
import io

from django.http import StreamingHttpResponse
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.suppressions.models import Bounce, Complaint, Suppression, Unsubscribe
from apps.suppressions.serializers import (
    DeleteSuppressionSerializer,
    SuppressionAddSerializer,
)


def _as_entry(email, sup_type, reason, created_at):
    return {"email": email, "type": sup_type, "reason": reason, "created_at": created_at}


class SuppressionListView(APIView):
    """List, add, or bulk-delete suppression entries."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Return suppression entries, optionally filtered by type and/or email substring."""
        sup_type = request.query_params.get("type")
        email_q = request.query_params.get("email", "").strip()

        results = []

        def _filter(qs):
            return qs.filter(email__icontains=email_q) if email_q else qs

        if sup_type in (None, "bounce"):
            for b in _filter(Bounce.objects.order_by("-created_at")):
                results.append(_as_entry(b.email, "bounce", b.reason, b.created_at))

        if sup_type in (None, "complaint"):
            for c in _filter(Complaint.objects.order_by("-created_at")):
                results.append(_as_entry(c.email, "complaint", c.feedback_type, c.created_at))

        if sup_type in (None, "unsubscribe"):
            for u in _filter(Unsubscribe.objects.order_by("-created_at")):
                results.append(_as_entry(u.email, "unsubscribe", u.source, u.created_at))

        # Include manual suppressions (per-user Suppression table)
        if sup_type in (None, "manual"):
            qs = Suppression.objects.filter(user=request.user)
            if email_q:
                qs = qs.filter(email__icontains=email_q)
            for s in qs.order_by("-created_at"):
                results.append(_as_entry(s.email, "manual", s.reason, s.created_at))

        if not sup_type:
            results.sort(key=lambda x: x["created_at"], reverse=True)

        return Response({"suppressions": results, "total": len(results)})

    def post(self, request):
        """Manually suppress an email address."""
        serializer = SuppressionAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].lower()
        sup_type = serializer.validated_data["type"]
        reason = serializer.validated_data["reason"]

        created = False
        if sup_type == "bounce":
            existing = Bounce.objects.filter(email__iexact=email).first()
            if not existing:
                Bounce.objects.create(email=email, reason=reason)
                created = True
        elif sup_type == "complaint":
            existing = Complaint.objects.filter(email__iexact=email).first()
            if not existing:
                Complaint.objects.create(email=email, feedback_type=reason)
                created = True
        elif sup_type == "manual":
            _, created = Suppression.objects.get_or_create(
                user=request.user,
                email=email,
                defaults={"reason": Suppression.REASON_MANUAL},
            )
        else:
            existing = Unsubscribe.objects.filter(email__iexact=email).first()
            if not existing:
                Unsubscribe.objects.create(email=email, source=reason or "manual")
                created = True

        return Response(
            {"email": email, "type": sup_type, "created": created},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request):
        """Bulk-remove emails from every suppression list."""
        serializer = DeleteSuppressionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        emails = serializer.validated_data["emails"]
        removed = _remove_emails(emails, user=request.user)
        return Response({"removed": removed, "emails": emails})


class SuppressionDetailView(APIView):
    """Delete a single email from all suppression lists."""

    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, email):
        """Remove a single email from every suppression table."""
        removed = _remove_emails([email], user=request.user)
        if removed == 0:
            return Response(
                {"detail": "Email not found in any suppression list."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


def _remove_emails(emails, user=None):
    """Delete every matching row across all suppression tables. Returns count removed."""
    removed = 0
    for email in emails:
        removed += Bounce.objects.filter(email__iexact=email).delete()[0]
        removed += Complaint.objects.filter(email__iexact=email).delete()[0]
        removed += Unsubscribe.objects.filter(email__iexact=email).delete()[0]
        if user:
            removed += Suppression.objects.filter(user=user, email__iexact=email).delete()[0]
    return removed


class SuppressionExportView(APIView):
    """GET /api/v1/suppressions/export/ — stream all suppressions as CSV."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        sup_type = request.query_params.get("type")

        def _rows():
            yield ["email", "type", "reason", "created_at"]

            if sup_type in (None, "bounce"):
                for b in Bounce.objects.order_by("email").values_list(
                    "email", "reason", "created_at"
                ):
                    yield [b[0], "bounce", b[1], b[2].isoformat()]

            if sup_type in (None, "complaint"):
                for c in Complaint.objects.order_by("email").values_list(
                    "email", "feedback_type", "created_at"
                ):
                    yield [c[0], "complaint", c[1], c[2].isoformat()]

            if sup_type in (None, "unsubscribe"):
                for u in Unsubscribe.objects.order_by("email").values_list(
                    "email", "source", "created_at"
                ):
                    yield [u[0], "unsubscribe", u[1], u[2].isoformat()]

            if sup_type in (None, "manual"):
                for s in Suppression.objects.filter(
                    user=request.user
                ).order_by("email").values_list("email", "reason", "created_at"):
                    yield [s[0], "manual", s[1], s[2].isoformat()]

        def _stream():
            for row in _rows():
                buf = io.StringIO()
                writer = csv.writer(buf)
                writer.writerow(row)
                yield buf.getvalue()

        response = StreamingHttpResponse(_stream(), content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="suppressions.csv"'
        return response
