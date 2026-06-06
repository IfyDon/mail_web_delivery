"""Custom DRF exception handler: standardised JSON error envelope."""
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    errors = []
    data = response.data

    if isinstance(data, dict):
        for field, messages in data.items():
            if isinstance(messages, list):
                for msg in messages:
                    errors.append({"field": field, "message": str(msg)})
            else:
                errors.append({"field": field, "message": str(messages)})
    elif isinstance(data, list):
        for msg in data:
            errors.append({"field": "non_field_errors", "message": str(msg)})
    else:
        errors.append({"field": "detail", "message": str(data)})

    response.data = {
        "status": "error",
        "code": response.status_code,
        "errors": errors,
    }
    return response
