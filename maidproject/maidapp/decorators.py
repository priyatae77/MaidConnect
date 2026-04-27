from django.shortcuts import redirect

from django.core.exceptions import PermissionDenied

def role_required(required_role):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            
            # Allow superuser to access admin views
            if required_role == 'admin' and request.user.is_superuser:
                return view_func(request, *args, **kwargs)
                
            if request.user.role != required_role:
                raise PermissionDenied()  # Returns 403
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def admin_required(view_func):
    return role_required('admin')(view_func)


def user_required(view_func):
    return role_required('user')(view_func)


def worker_required(view_func):
    return role_required('worker')(view_func)