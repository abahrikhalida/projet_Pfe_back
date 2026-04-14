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


# class IsDiVisionnaire(BasePermission):
#     def has_permission(self, request, view):
#         return get_role(request.user) in ('directeur', 'divisionnaire')
class IsDivisionnaire(BasePermission):
    def has_permission(self, request, view):
        return get_role(request.user) == 'divisionnaire'



# class IsChef(BasePermission):
#     def has_permission(self, request, view):
#         return get_role(request.user) in ('directeur', 'divisionnaire', 'chef')
class IsChef(BasePermission):
    def has_permission(self, request, view):
        return get_role(request.user) == 'chef'
# class IsAgent(BasePermission):
#     def has_permission(self, request, view):
#         return get_role(request.user) == 'agent'

class IsAgent(BasePermission):
    """Tous les rôles authentifiés"""
    def has_permission(self, request, view):
        return get_role(request.user) in (
            'directeur',
            'directeur_region',
            'divisionnaire',
            'chef',
            'responsable_structure',
            'agent',
        )
class IsResponsableStructure(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'role', None) == 'responsable_structure'
        )
# permissions.py — ajouter ce qui manque
class IsDirecteurRegion(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'role', None) == 'directeur_region'
        )