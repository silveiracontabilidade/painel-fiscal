from django.urls import path

from . import api_views

urlpatterns = [
    path(
        'auditores/posicao-geral/',
        api_views.DctfwebPosicaoGeralView.as_view(),
        name='auditores_posicao_geral',
    ),
]
