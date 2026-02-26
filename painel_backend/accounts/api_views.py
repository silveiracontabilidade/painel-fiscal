from django.contrib.auth import get_user_model
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Grupo, GrupoUsuario

DEFAULT_PASSWORD = 'Mudar123'
User = get_user_model()


def _user_profile(user: User) -> str:
    return 'administrador' if user.is_staff or user.is_superuser else 'analista'


class UserSerializer(serializers.ModelSerializer):
    profile = serializers.ChoiceField(choices=['administrador', 'analista'], write_only=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    group_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    group = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'profile', 'password', 'group_id', 'group']
        extra_kwargs = {
            'username': {'required': True},
            'email': {'required': False, 'allow_blank': True},
        }

    def get_group(self, instance: User):
        membership = getattr(instance, 'grupo_membership', None)
        if not membership:
            return None
        grupo = membership.grupo
        return {'id': grupo.id, 'nome': grupo.nome}

    def to_representation(self, instance: User):
        data = super().to_representation(instance)
        data['profile'] = _user_profile(instance)
        data.pop('password', None)
        return data

    def _apply_group(self, user: User, group_value):
        if group_value is serializers.empty:
            return
        if group_value is None:
            GrupoUsuario.objects.filter(user=user).delete()
            return
        grupo = Grupo.objects.filter(pk=group_value).first()
        if not grupo:
            raise serializers.ValidationError({'group_id': 'Grupo não encontrado.'})
        GrupoUsuario.objects.update_or_create(user=user, defaults={'grupo': grupo})

    def create(self, validated_data):
        profile = validated_data.pop('profile', 'analista')
        group_value = validated_data.pop('group_id', serializers.empty)
        raw_password = validated_data.pop('password', None) or DEFAULT_PASSWORD
        user = User(**validated_data)
        user.is_staff = profile == 'administrador'
        user.is_superuser = False
        user.set_password(raw_password)
        user.save()
        self._apply_group(user, group_value)
        return user

    def update(self, instance: User, validated_data):
        profile = validated_data.pop('profile', None)
        group_value = validated_data.pop('group_id', serializers.empty)
        validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if profile:
            instance.is_staff = profile == 'administrador'
            if profile == 'analista':
                instance.is_superuser = False
        instance.save()
        self._apply_group(instance, group_value)
        return instance


class GroupSerializer(serializers.ModelSerializer):
    coordenador_id = serializers.PrimaryKeyRelatedField(
        source='coordenador', queryset=User.objects.all(), required=False, allow_null=True, write_only=True
    )
    coordenador = serializers.SerializerMethodField()

    class Meta:
        model = Grupo
        fields = ['id', 'nome', 'coordenador_id', 'coordenador']

    def get_coordenador(self, instance: Grupo):
        if not instance.coordenador:
            return None
        return {
            'id': instance.coordenador.id,
            'username': instance.coordenador.username,
            'email': instance.coordenador.email or '',
        }


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
        users = User.objects.order_by('username').select_related('grupo_membership__grupo')
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
        return User.objects.select_related('grupo_membership__grupo').filter(pk=pk).first()

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


class GroupListCreateView(AdminRequiredMixin, APIView):
    def get(self, request):
        forbidden = self.ensure_admin(request)
        if forbidden:
            return forbidden
        groups = Grupo.objects.order_by('nome')
        serializer = GroupSerializer(groups, many=True)
        return Response({'results': serializer.data})

    def post(self, request):
        forbidden = self.ensure_admin(request)
        if forbidden:
            return forbidden
        serializer = GroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group = serializer.save()
        return Response(GroupSerializer(group).data, status=status.HTTP_201_CREATED)


class GroupDetailView(AdminRequiredMixin, APIView):
    def get_object(self, pk: int):
        return Grupo.objects.filter(pk=pk).first()

    def get(self, request, pk: int):
        forbidden = self.ensure_admin(request)
        if forbidden:
            return forbidden
        group = self.get_object(pk)
        if not group:
            return Response({'detail': 'Grupo não encontrado.'}, status=404)
        return Response(GroupSerializer(group).data)

    def patch(self, request, pk: int):
        forbidden = self.ensure_admin(request)
        if forbidden:
            return forbidden
        group = self.get_object(pk)
        if not group:
            return Response({'detail': 'Grupo não encontrado.'}, status=404)
        serializer = GroupSerializer(group, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        group = serializer.save()
        return Response(GroupSerializer(group).data)

    def delete(self, request, pk: int):
        forbidden = self.ensure_admin(request)
        if forbidden:
            return forbidden
        group = self.get_object(pk)
        if not group:
            return Response({'detail': 'Grupo não encontrado.'}, status=404)
        group.delete()
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
