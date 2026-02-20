from django.http import JsonResponse


def make_error_json_response(error_message, status_code):
    return JsonResponse({"error": error_message}, status=status_code)


def make_success_json_response(status_code, message="Success", response_body=None):
    if response_body:
        return JsonResponse(response_body, status=status_code)
    return JsonResponse({"message": message}, status=status_code)
