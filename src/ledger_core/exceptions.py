from rest_framework.views import exception_handler


def core_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        response.data = {
            "error": True,
            "detail": response.data,
        }
    return response
