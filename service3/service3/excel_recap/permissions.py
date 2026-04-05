# # service3/budget/permissions.py
# from rest_framework.permissions import BasePermission


# class IsDirecteur(BasePermission):
#     def has_permission(self, request, view):
#         return getattr(request.user, 'role', None) == 'directeur'


# class IsVisionnaire(BasePermission):
#     def has_permission(self, request, view):
#         return getattr(request.user, 'role', None) in ('directeur', 'visionnaire')


# class IsChef(BasePermission):
#     def has_permission(self, request, view):
#         return getattr(request.user, 'role', None) in ('directeur', 'visionnaire', 'chef')


# class IsAgent(BasePermission):
#     """Tous les rôles authentifiés."""
#     def has_permission(self, request, view):
#         return getattr(request.user, 'role', None) in ('directeur', 'visionnaire', 'chef', 'agent')
from rest_framework.permissions import BasePermission


def get_role(user):
    return str(getattr(user, 'role', '')).lower().strip()


class IsDirecteur(BasePermission):
    def has_permission(self, request, view):
        return get_role(request.user) == 'directeur'


class IsVisionnaire(BasePermission):
    def has_permission(self, request, view):
        return get_role(request.user) in ('directeur', 'visionnaire')


class IsChef(BasePermission):
    def has_permission(self, request, view):
        return get_role(request.user) in ('directeur', 'visionnaire', 'chef')


class IsAgent(BasePermission):
    def has_permission(self, request, view):
        return get_role(request.user) in ('directeur', 'visionnaire', 'chef', 'agent')