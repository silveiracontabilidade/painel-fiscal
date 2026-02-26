from django.contrib import admin

from .models import Grupo, GrupoUsuario


@admin.register(Grupo)
class GrupoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'coordenador')
    search_fields = ('nome',)


@admin.register(GrupoUsuario)
class GrupoUsuarioAdmin(admin.ModelAdmin):
    list_display = ('user', 'grupo')
    search_fields = ('user__username', 'grupo__nome')
