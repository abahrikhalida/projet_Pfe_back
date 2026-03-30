from rest_framework import serializers
from .models import Agent,User


from rest_framework import serializers
from .models import User
import cloudinary.uploader
from django.contrib.auth.hashers import make_password
import secrets

class UserSerializer(serializers.ModelSerializer):
    photo_profil = serializers.ImageField(required=False)

    class Meta:
        model = User
        fields = ["id", "email", "nom", "prenom", "password", "is_staff", "is_superuser", "photo_profil"]
        extra_kwargs = {"password": {"write_only": True, "required": False}}

    def create(self, validated_data):
        photo = validated_data.pop("photo_profil", None)
        if "password" not in validated_data or not validated_data["password"]:
            generated_password = secrets.token_urlsafe(8)
            validated_data["password"] = make_password(generated_password)
            self.generated_password = generated_password

        if photo:
            result = cloudinary.uploader.upload(photo)
            validated_data["photo_profil"] = result["secure_url"]

        user = super().create(validated_data)
        user.generated_password = getattr(self, "generated_password", None)
        return user

class AgentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        fields = ['id', 'nom', 'prenom', 'email', 'adresse', 'date_naissance',
                  'sexe', 'telephone', 'matricule', 'is_activated']