from django.contrib.auth import get_user_model
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

DEFAULT_PASSWORD = 'Mudar123'
User = get_user_model()


def _user_profile(user: User) -> str:
    return 'administrador' if user.is_staff or user.is_superuser else 'analista'


class UserSerializer(serializers.ModelSerializer):
    profile = serializers.ChoiceField(choices=['administrador', 'analista'], write_only=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'profile', 'password']
        extra_kwargs = {
            'username': {'required': True},
            'email': {'required': False, 'allow_blank': True},
        }

    def to_representation(self, instance: User):
        data = super().to_representation(instance)
        data['profile'] = _user_profile(instance)
        data.pop('password', None)
        return data

    def create(self, validated_data):
        profile = validated_data.pop('profile', 'analista')
        raw_password = validated_data.pop('password', None) or DEFAULT_PASSWORD
        user = User(**validated_data)
        user.is_staff = profile == 'administrador'
        user.is_superuser = False
        user.set_password(raw_password)
        user.save()
        return user

    def update(self, instance: User, validated_data):
        profile = validated_data.pop('profile', None)
        validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if profile:
            instance.is_staff = profile == 'administrador'
            if profile == 'analista':
                instance.is_superuser = False
        instance.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    currentPassword = serializers.CharField()
    newPassword = serializers.CharField()

    def validate_newPassword(self, value: str) -> str:
        if len(value.strip()) < 6:
            raise serializers.ValidationError('A nova senha deve ter ao menos 6 caracteres.')
        return value

    def save(self, **kwargs):
        user: User = self.context['user']
        current_password = self.validated_data['currentPassword']
        if not user.check_password(current_password):
            raise serializers.ValidationError({'currentPassword': 'Senha atual incorreta.'})
        user.set_password(self.validated_data['newPassword'])
        user.save(update_fields=['password'])
        return user


class AdminRequiredMixin:
    permission_classes = [IsAuthenticated]

    def is_admin(self, request):
        return bool(request.user and (request.user.is_staff or request.user.is_superuser))

    def ensure_admin(self, request):
        if not self.is_admin(request):
            return Response({'detail': 'Acesso restrito a administradores.'}, status=403)
        return None


class UserListCreateView(AdminRequiredMixin, APIView):
    def get(self, request):
        forbidden = self.ensure_admin(request)
        if forbidden:
            return forbidden
        users = User.objects.order_by('username')
        serializer = UserSerializer(users, many=True)
        return Response({'results': serializer.data})

    def post(self, request):
        forbidden = self.ensure_admin(request)
        if forbidden:
            return forbidden
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class UserDetailView(AdminRequiredMixin, APIView):
    def get_object(self, pk: int):
        return User.objects.filter(pk=pk).first()

    def get(self, request, pk: int):
        forbidden = self.ensure_admin(request)
        if forbidden:
            return forbidden
        user = self.get_object(pk)
        if not user:
            return Response({'detail': 'Usuário não encontrado.'}, status=404)
        return Response(UserSerializer(user).data)

    def patch(self, request, pk: int):
        forbidden = self.ensure_admin(request)
        if forbidden:
            return forbidden
        user = self.get_object(pk)
        if not user:
            return Response({'detail': 'Usuário não encontrado.'}, status=404)
        serializer = UserSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data)

    def delete(self, request, pk: int):
        forbidden = self.ensure_admin(request)
        if forbidden:
            return forbidden
        user = self.get_object(pk)
        if not user:
            return Response({'detail': 'Usuário não encontrado.'}, status=404)
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ResetPasswordView(AdminRequiredMixin, APIView):
    def post(self, request, pk: int):
        forbidden = self.ensure_admin(request)
        if forbidden:
            return forbidden
        user = User.objects.filter(pk=pk).first()
        if not user:
            return Response({'detail': 'Usuário não encontrado.'}, status=404)
        user.set_password(DEFAULT_PASSWORD)
        user.save(update_fields=['password'])
        return Response({'detail': 'Senha redefinida para o padrão.'})


class ChangeOwnPasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'user': request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'Senha atualizada com sucesso.'})
