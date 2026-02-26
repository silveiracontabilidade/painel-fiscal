from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Grupo(models.Model):
    nome = models.CharField(max_length=120, unique=True)
    coordenador = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='grupos_coordenados',
    )

    class Meta:
        verbose_name = 'Grupo'
        verbose_name_plural = 'Grupos'

    def __str__(self) -> str:
        return self.nome


class GrupoUsuario(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='grupo_membership')
    grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE, related_name='usuarios')

    class Meta:
        verbose_name = 'Grupo do usuário'
        verbose_name_plural = 'Grupos dos usuários'
