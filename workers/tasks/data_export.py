"""Celery task: build a user's GDPR data export in the background."""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_data_export_task(self, export_request_id: int) -> dict:
    from apps.accounts.models import DataExportRequest
    from services.gdpr_service import build_data_export, save_export_file

    try:
        export_request = DataExportRequest.objects.select_related("user").get(pk=export_request_id)
    except DataExportRequest.DoesNotExist:
        logger.warning("generate_data_export_task: request %s not found", export_request_id)
        return {"status": "error", "reason": "request_not_found"}

    export_request.status = DataExportRequest.STATUS_PROCESSING
    export_request.save(update_fields=["status"])

    try:
        content = build_data_export(export_request.user)
        save_export_file(export_request, content)
    except Exception as exc:  # noqa: BLE001
        logger.exception("generate_data_export_task: failed for request=%s", export_request_id)
        export_request.status = DataExportRequest.STATUS_FAILED
        export_request.save(update_fields=["status"])
        raise self.retry(exc=exc, countdown=60) from exc

    logger.info("generate_data_export_task: ready request=%s", export_request_id)
    return {"status": "ready", "request_id": export_request_id}
