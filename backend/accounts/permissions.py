from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from django.core.cache import cache
from django.http import HttpRequest
from django.utils.functional import cached_property
from typing import Optional, Set, Tuple, Union
from accounts.models import User 

from rest_framework.permissions import SAFE_METHODS

"""
    rest_framework have this permissions it self
    (from rest_framework.permissions import ...)
        AllowAny
        IsAuthenticated
        IsAdminUser
        IsAuthenticatedOrReadOnly
"""


class HasDynamicPermission(BasePermission):
    """
    Custom permission:
    - Deny anonymous users.
    - Allow superusers.
    - For regular users: check role-based API access using cached permissions.
    """

    def get_base_url(self, request: Union[Request, HttpRequest]) -> Optional[str]:
        """
        Extracts the static base route from the resolved URL pattern.
        """
        route = getattr(request, "resolver_match", None)
        if route and hasattr(route, "route"):
            # route.split('<') : trims off any dynamic parts (like <int:id>) from the route.
            return '/' + route.route.split('<')[0].rstrip('/') + '/'
        return None

    def get_cached_permissions(self, user: User) -> Set[Tuple[str, str]]:
        """
        Fetches allowed (method, url) tuples for the user’s role from cache or DB.
        """
        role = getattr(user, "roles", None)
        if not role:
            return set()

        cache_key = f"user:{user.id}:role:{role.id}:allowed_apis"
        allowed: Optional[Set[Tuple[str, str]]] = cache.get(cache_key)
        if allowed is None:
            allowed = set(
                role.apis.values_list("method", "url")
            )
            cache.set(cache_key, allowed, timeout=3600)  # Cache for 1 hour

        return allowed

    def has_permission(self, request: Request, view) -> bool:
        user: User = request.user

        # 1. Must be authenticated
        if not user or not user.is_authenticated:
            return False

        # 2. Superuser gets full access
        if user.is_superuser:
            return True

        # 3. Extract route
        base_url: Optional[str] = self.get_base_url(request)
        if not base_url:
            return False

        # 4. Get allowed API actions
        allowed_apis = self.get_cached_permissions(user)

        # 5. Check permission tuple
        return (request.method, base_url) in allowed_apis

class IsAdminSuperUserOrReadOnly(BasePermission):
    """
        Only allow ADMIN users to edit or delete objects.
        Non-admin users can only view (read-only).
    """

    def has_permission(self, request, view):
        # Check if the request method is "safe" (GET, HEAD, OPTIONS).
        if request.method in SAFE_METHODS:
            return True  # Allow read-only access for any user

        # For other methods (POST, PUT, DELETE), check if the user is an admin
        return bool(request.user and request.user.is_superuser)  # Allow only if the user is admin

class IsAdminSuperUser(BasePermission):
    """
    Allows access only to superuser users.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_superuser)