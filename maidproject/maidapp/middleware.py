from django.shortcuts import redirect
from django.contrib.auth import logout
from django.urls import reverse

class SingleDeviceSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Check if current session matches the stored session key
            stored_session_key = getattr(request.user, 'session_key', None)
            if stored_session_key and request.session.session_key != stored_session_key:
                logout(request)
                return redirect('login')
        return self.get_response(request)


class RestrictPublicPagesMiddleware:
    """Redirect authenticated users away from login/register pages"""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            public_paths = [reverse('login'), reverse('register_choice'), reverse('user_register'), reverse('worker_register')]
            if request.path in public_paths:
                role = request.user.role
                if role == 'admin' or request.user.is_superuser:
                    return redirect('admin_dashboard')
                elif role == 'worker':
                    return redirect('worker_dashboard')
                else:
                    return redirect('user_dashboard')
        return self.get_response(request)


class RoleBasedAccessMiddleware:
    """Strictly enforce that users only access pages meant for their role"""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            path = request.path
            role = request.user.role

            # Admin has full access
            if request.user.is_superuser or role == 'admin':
                return self.get_response(request)

            # Strict isolation logic
            if '/dashboard/admin/' in path or '/admin/' in path:
                if role != 'admin':
                    return self.redirect_by_role(role)

            if '/dashboard/worker/' in path or '/worker/' in path:
                if role != 'worker':
                    return self.redirect_by_role(role)

            if '/dashboard/user/' in path or '/user/' in path:
                if role != 'user':
                    return self.redirect_by_role(role)

        return self.get_response(request)

    def redirect_by_role(self, role):
        if role == 'worker':
            return redirect('worker_dashboard')
        elif role == 'user':
            return redirect('user_dashboard')
        return redirect('home')
