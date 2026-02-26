import csv
from io import BytesIO
from typing import Dict, List, Optional

from django.db import connections
from django.http import HttpResponse
from django.utils import timezone
from openpyxl import Workbook
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import VwDctfwebPosicaoGeral
from .serializers import DctfwebPosicaoGeralSerializer


def _dictfetchall(cursor) -> List[Dict[str, object]]:
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _listar_competencias_dctfweb() -> List[str]:
    sql = """
        SELECT
            competencia
        FROM dctfweb_posicao
        WHERE competencia IS NOT NULL AND competencia <> ''
        GROUP BY competencia
        ORDER BY STR_TO_DATE(CONCAT('01/', competencia), '%d/%m/%Y') DESC
    """
    with connections['automacoesdp'].cursor() as cursor:
        cursor.execute(sql)
        return [row[0] for row in cursor.fetchall() if row[0]]


def _buscar_ultimas_atualizacoes_dctfweb(limite: Optional[int] = None) -> List[Dict[str, object]]:
    sql = """
        SELECT
            competencia,
            MAX(data_captura) AS ultima_atualizacao
        FROM dctfweb_posicao
        GROUP BY competencia
        ORDER BY STR_TO_DATE(CONCAT('01/', competencia), '%d/%m/%Y') DESC
    """
    if limite is not None:
        sql += f" LIMIT {int(limite)}"
    with connections['automacoesdp'].cursor() as cursor:
        cursor.execute(sql)
        registros = _dictfetchall(cursor)
    for registro in registros:
        valor = registro.get('ultima_atualizacao')
        if hasattr(valor, 'isoformat'):
            if timezone.is_naive(valor):
                valor = timezone.make_aware(valor, timezone.get_current_timezone())
            registro['ultima_atualizacao'] = timezone.localtime(valor).isoformat()
    return registros


def _selecionar_competencia(valor: Optional[str], opcoes: List[str]) -> Optional[str]:
    valor_normalizado = (valor or '').strip()
    if valor_normalizado and valor_normalizado in opcoes:
        return valor_normalizado
    return opcoes[0] if opcoes else None


def _filtrar_queryset_por_competencia(queryset, competencia: Optional[str]):
    if not competencia:
        return queryset
    where_sql = """
        cod_folha IN (
            SELECT DISTINCT cod_folha
            FROM dctfweb_posicao
            WHERE competencia = %s
        )
    """
    return queryset.extra(where=[where_sql], params=[competencia])

def _export_csv(rows: List[Dict[str, object]]) -> HttpResponse:
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=dctfweb_posicao_geral.csv'
    writer = csv.writer(response)
    writer.writerow(
        [
            'FOLHA',
            'RAZAO_SOCIAL',
            'CNPJ',
            'INICIO',
            'TERMINO',
            'SISTEMA',
            'ORIGEM',
            'CLASSIFICACAO',
            'TIPO',
            'SITUACAO',
            'SALDO_PAGAR',
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row.get('cod_folha'),
                row.get('razao_social'),
                row.get('cnpj_original'),
                row.get('inicio_contrato'),
                row.get('termino_contrato'),
                row.get('sistema'),
                row.get('origem'),
                row.get('classificacao2'),
                row.get('tipo'),
                row.get('situacao'),
                row.get('saldo_pagar_formatado'),
            ]
        )
    return response


def _export_excel(rows: List[Dict[str, object]]) -> HttpResponse:
    wb = Workbook()
    ws = wb.active
    ws.title = 'Posicao geral'
    headers = [
        'FOLHA',
        'RAZAO_SOCIAL',
        'CNPJ',
        'INICIO',
        'TERMINO',
        'SISTEMA',
        'ORIGEM',
        'CLASSIFICACAO',
        'TIPO',
        'SITUACAO',
        'SALDO_PAGAR',
    ]
    ws.append(headers)
    for row in rows:
        ws.append(
            [
                row.get('cod_folha'),
                row.get('razao_social'),
                row.get('cnpj_original'),
                row.get('inicio_contrato'),
                row.get('termino_contrato'),
                row.get('sistema'),
                row.get('origem'),
                row.get('classificacao2'),
                row.get('tipo'),
                row.get('situacao'),
                row.get('saldo_pagar_formatado'),
            ]
        )
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename=dctfweb_posicao_geral.xlsx'
    return response


class DctfwebPosicaoGeralView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        competencias_disponiveis = _listar_competencias_dctfweb()
        competencia_param = request.query_params.get('competencia')
        competencia_selecionada = _selecionar_competencia(
            competencia_param, competencias_disponiveis
        )
        queryset = VwDctfwebPosicaoGeral.objects.using('automacoesdp').all()
        queryset = _filtrar_queryset_por_competencia(queryset, competencia_selecionada)
        serializer = DctfwebPosicaoGeralSerializer(queryset, many=True)
        export = (request.query_params.get('export') or '').lower().strip()
        if export in {'csv', 'excel'}:
            data = serializer.data
            if export == 'csv':
                return _export_csv(data)
            return _export_excel(data)
        payload = {
            'competencias': competencias_disponiveis,
            'competencia_selecionada': competencia_selecionada,
            'ultimas_atualizacoes': _buscar_ultimas_atualizacoes_dctfweb(),
            'results': serializer.data,
        }
        return Response(payload)
