from functools import wraps

from django.http import JsonResponse

def clerk_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user or request.user.is_anonymous:
            return JsonResponse({"error": "Unauthorized"}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper

def role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = request.user

            if not user or request.user.is_anonymous:
                return JsonResponse({"error": "Unauthorized"}, status=401)
            if user.role not in allowed_roles:
                return JsonResponse({
                    "error": "Forbidden",
                    "message": f"This action requires one of these roles: {', '.join(allowed_roles)}",
                    }, status=403)

            return view_func(request, *args, **kwargs)
        
        return wrapper
    
    return decorator

def any_authenticated_user(view_func):
    return clerk_login_required(view_func)

def kiosk_or_above(view_func):
    return role_required("kiosk", "teacher", "admin", "owner")(view_func)

def teacher_or_above(view_func):
    return role_required("teacher", "admin", "owner")(view_func)

def admin_or_owner(view_func):
    return role_required("admin", "owner")(view_func)

def owner_only(view_func):
    return role_required("owner")(view_func)
