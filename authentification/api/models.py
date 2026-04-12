
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, Group, Permission
from django.utils.crypto import get_random_string
from django.core.mail import send_mail
from django.conf import settings
from cloudinary.models import CloudinaryField
from jsonschema import ValidationError


# ===============================
# CUSTOM USER MANAGER
# ===============================
class CustomUserManager(BaseUserManager):
    def create_user(self, email, nom, prenom, role, password=None, **extra_fields):
        if not email:
            raise ValueError("Email obligatoire")
        email = self.normalize_email(email)
        user = self.model(email=email, nom=nom, prenom=prenom, role=role, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_password(get_random_string(8))
        user.save(using=self._db)
        return user

    def create_superuser(self, email, nom, prenom, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email=email, nom=nom, prenom=prenom, role='admin', password=password, **extra_fields)


# ===============================
# USER MODEL
# ===============================
# ancien model de user 
# class User(AbstractBaseUser, PermissionsMixin):

#     ROLE_CHOICES = [
#         ('admin', 'Admin'),
#         ('directeur', 'Directeur'),
#         ('visionnaire', 'Visionnaire'),
#         ('chef', 'Chef Departement'),
#         ('agent', 'Agent'),
#     ]

#     email = models.EmailField(unique=True)
#     nom = models.CharField(max_length=50)
#     prenom = models.CharField(max_length=50)
#     role = models.CharField(max_length=20, choices=ROLE_CHOICES)
#     photo_profil = CloudinaryField('image', blank=True, null=True)

#     is_active = models.BooleanField(default=True)
#     is_staff = models.BooleanField(default=False)
#     is_superuser = models.BooleanField(default=False)

#     groups = models.ManyToManyField(Group, related_name="custom_user_groups", blank=True)
#     user_permissions = models.ManyToManyField(Permission, related_name="custom_user_permissions", blank=True)

#     objects = CustomUserManager()

#     USERNAME_FIELD = 'email'
#     REQUIRED_FIELDS = ['nom', 'prenom']

#     def __str__(self):
#         return f"{self.nom} {self.prenom} ({self.role})"

#     def has_perm(self, perm, obj=None):
#         return self.is_superuser

#     def has_module_perms(self, app_label):
#         return self.is_superuser


#new model user 
# ===============================
# USER MODEL — champs région/structure
# ===============================
class User(AbstractBaseUser, PermissionsMixin):

    ROLE_CHOICES = [
        ('admin',                 'Admin'),
        ('chef',                  'Chef'),
        ('directeur',             'Directeur'),
        ('directeur_region',      'Directeur de Région'),
        ('responsable_structure', 'Responsable de Structure'),
        ('divisionnaire',         'Divisionnaire'),
        ('agent',                 'Agent'),
    ]

    email        = models.EmailField(unique=True)
    nom          = models.CharField(max_length=50)
    prenom       = models.CharField(max_length=50)
    role         = models.CharField(max_length=30, choices=ROLE_CHOICES)
    photo_profil = CloudinaryField('image', blank=True, null=True)

    # IDs MongoDB — pas de ForeignKey, juste des références externes
    region_id    = models.CharField(max_length=24, blank=True, null=True)  # ObjectId MongoDB
    structure_id = models.CharField(max_length=24, blank=True, null=True)  # ObjectId MongoDB

    is_active    = models.BooleanField(default=True)
    is_staff     = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    groups           = models.ManyToManyField(Group, related_name="custom_user_groups", blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name="custom_user_permissions", blank=True)

    objects = CustomUserManager()

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['nom', 'prenom']

    def __str__(self):
        return f"{self.nom} {self.prenom} ({self.role})"

    # def clean(self):
    #     if self.role == 'directeur_region':
    #         if not self.region_id:
    #             raise ValidationError("Un directeur de région doit avoir un region_id.")
    #         self.structure_id = None

    #     elif self.role == 'responsable_structure':
    #         if not self.structure_id:
    #             raise ValidationError("Un responsable de structure doit avoir un structure_id.")
    #         if not self.region_id:
    #             raise ValidationError("Un responsable de structure doit avoir un region_id.")

    #     elif self.role in ('admin', 'chef', 'directeur', 'divisionnaire', 'agent'):
    #         self.region_id    = None
    #         self.structure_id = None
    def clean(self):
        # Ne valider region/structure que si explicitement fournis
        if self.role == 'directeur_region' and self.region_id:
            self.structure_id = None

        elif self.role == 'responsable_structure' and self.structure_id:
            if not self.region_id:
                raise ValidationError("Un responsable de structure doit avoir un region_id.")

        elif self.role in ('admin', 'chef', 'directeur', 'divisionnaire', 'agent'):
            self.region_id    = None
            self.structure_id = None

    def has_perm(self, perm, obj=None):
        return self.is_superuser

    def has_module_perms(self, app_label):
        return self.is_superuser

# ===============================
# ADMIN MODEL
# ===============================
class Admin(User):
    objects = CustomUserManager()

    class Meta:
        verbose_name = "Admin"
        verbose_name_plural = "Admins"

    def save(self, *args, **kwargs):
        self.is_staff = True
        self.is_superuser = True
        super().save(*args, **kwargs)


# ===============================
# AGENT MODEL
# ===============================
class Agent(models.Model):
    chef = models.ForeignKey(User, on_delete=models.CASCADE, related_name="agents")
    nom = models.CharField(max_length=50)
    prenom = models.CharField(max_length=50)
    adresse = models.TextField()
    email = models.EmailField(unique=True)
    date_naissance = models.DateField()

    SEXE_CHOICES = [('M', 'Masculin'), ('F', 'Féminin')]
    sexe = models.CharField(max_length=1, choices=SEXE_CHOICES)

    telephone = models.CharField(max_length=20)
    matricule = models.CharField(max_length=20, unique=True)
    poste = models.CharField(max_length=100)

    password_temp = models.CharField(max_length=20, blank=True, null=True)
    activation_code = models.CharField(max_length=6, blank=True, null=True)
    is_activated = models.BooleanField(default=False)

    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)  # pour login

    def save(self, *args, **kwargs):
        if not self.pk:
            # Générer mot de passe temporaire et code d’activation
            temp_password = get_random_string(8)
            self.password_temp = temp_password
            self.activation_code = get_random_string(6)
            self.is_activated = True

            # Créer User lié à l'agent
            if not self.user:
                self.user = User.objects.create_user(
                    email=self.email,
                    nom=self.nom,
                    prenom=self.prenom,
                    role='agent',
                    password=temp_password
                )

            # Envoyer email automatique à l’agent
            send_mail(
                subject="Votre compte Agent",
                message=f"""
Bonjour {self.nom},

Votre compte a été créé par le chef departement {self.chef.nom} {self.chef.prenom} ({self.chef.email}).

Voici vos identifiants de connexion :

Email : {self.email}
Mot de passe : {temp_password}

Merci.
""",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.email],
                fail_silently=False,
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nom} {self.prenom} ({self.email})"
    