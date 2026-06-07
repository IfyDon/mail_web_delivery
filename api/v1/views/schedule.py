"""DELETE /api/v1/messages/{id}/schedule/ — cancel a scheduled message."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.email_messages.models import Message


class CancelScheduleView(APIView):
    def delete(self, request, pk):
        try:
            msg = Message.objects.get(pk=pk, user=request.user)
        except Message.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if msg.status != Message.STATUS_SCHEDULED:
            return Response(
                {"detail": "Only scheduled messages can be cancelled."},
                status=status.HTTP_409_CONFLICT,
            )

        msg.status = Message.STATUS_CANCELLED
        msg.save(update_fields=["status", "updated_at"])
        return Response(
            {"message_id": str(msg.pk), "status": msg.status},
            status=status.HTTP_200_OK,
        )
