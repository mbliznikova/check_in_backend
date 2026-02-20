from django.http import JsonResponse


# Default configuration constants
DEFAULT_CLASS_NAME = "No name class"
DEFAULT_CLASS_DURATION_MINUTES = 60
DEFAULT_DAY_START_TIME = "08:00"
DEFAULT_DAY_END_TIME = "21:00"
DEFAULT_TIME_SLOT_STEP_MINUTES = 30


def make_error_json_response(error_message, status_code):
    return JsonResponse({"error": error_message}, status=status_code)


def make_success_json_response(status_code, message="Success", response_body=None):
    if response_body:
        return JsonResponse(response_body, status=status_code)
    return JsonResponse({"message": message}, status=status_code)
