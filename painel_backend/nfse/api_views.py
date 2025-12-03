import io
import uuid
import zipfile
from pathlib import Path

from django.db import models
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from openpyxl import Workbook
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ImportJob, ImportJobFile, PayrollCompany
from .serializers import (
    ImportJobCreateSerializer,
    ImportJobDetailSerializer,
    ImportJobSerializer,
    ReprocessSerializer,
)
from .tasks import enqueue_job


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_file(request):
    file_obj = request.FILES.get('file')
    if not file_obj:
        return Response({'detail': 'Arquivo é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)

    today_path = timezone.now().strftime('%Y/%m/%d')
    target = Path('nfse/uploads') / today_path / f'{uuid.uuid4()}_{file_obj.name}'
    saved_name = default_storage.save(str(target), file_obj)

    payload = {
        'fileId': str(uuid.uuid4()),
        'fileName': file_obj.name,
        'size': file_obj.size,
        'uploadToken': saved_name,
    }
    return Response(payload, status=status.HTTP_201_CREATED)


class ImportJobListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        page_size = min(int(request.query_params.get('page_size', 20)), 100)
        jobs = ImportJob.objects.prefetch_related('files')[:page_size]
        serializer = ImportJobSerializer(
            jobs, many=True, context={'request': request}
        )
        return Response({'results': serializer.data})

    def post(self, request):
        serializer = ImportJobCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        job = ImportJob.objects.create(
            options=validated.get('options') or {},
            status=ImportJob.Status.PENDING,
        )

        helper = JobFileBuilder()
        job_files = []
        try:
            for descriptor in validated['files']:
                job_files.extend(helper.prepare_job_files(job, descriptor))
        except ValidationError:
            job.delete()
            raise

        if not job_files:
            job.delete()
            return Response(
                {'detail': 'Nenhum arquivo PDF válido foi encontrado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ImportJobFile.objects.bulk_create(job_files)
        job.refresh_totals()
        job = ImportJob.objects.prefetch_related('files').get(pk=job.pk)

        enqueue_job(str(job.id))
        detail = ImportJobDetailSerializer(job, context={'request': request})
        return Response(detail.data, status=status.HTTP_201_CREATED)


class ImportJobDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        job = get_object_or_404(ImportJob.objects.prefetch_related('files'), pk=pk)
        serializer = ImportJobDetailSerializer(job, context={'request': request})
        return Response(serializer.data)

    def delete(self, request, pk):
        job = get_object_or_404(ImportJob.objects.prefetch_related('files'), pk=pk)
        job.files.all().delete()
        job.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ImportJobReprocessView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        job = get_object_or_404(ImportJob, pk=pk)
        serializer = ReprocessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file_ids = serializer.validated_data['fileIds']

        files = list(job.files.filter(id__in=file_ids))
        if not files:
            return Response(
                {'detail': 'Nenhum arquivo encontrado para reprocessar.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        for job_file in files:
            job_file.status = ImportJobFile.Status.PENDING
            job_file.stage = ImportJobFile.Stage.QUEUED
            job_file.progress = 0
            job_file.message = ''
            job_file.result = None
            job_file.save(update_fields=['status', 'stage', 'progress', 'message', 'result'])

        job.status = ImportJob.Status.PENDING
        job.save(update_fields=['status'])
        enqueue_job(str(job.id))

        job.refresh_totals()
        detail = ImportJobDetailSerializer(job, context={'request': request})
        return Response(detail.data)


class CompanySearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        search = (request.query_params.get('search') or '').strip()
        qs = PayrollCompany.objects.filter(matriz__iexact='sim')
        if search:
            qs = qs.filter(
                models.Q(cod_folha__icontains=search)
                | models.Q(razao_social__icontains=search)
            )
        companies = qs.order_by('cod_folha')[:25]
        payload = [
            {'code': item.cod_folha, 'name': item.razao_social} for item in companies
        ]
        return Response({'results': payload})


class JobDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, category: str):
        job = get_object_or_404(ImportJob.objects.prefetch_related('files'), pk=pk)
        category = category.lower()
        if category not in {'services', 'others', 'services-excel'}:
            return Response(
                {'detail': 'Categoria inválida.'}, status=status.HTTP_400_BAD_REQUEST
            )

        if category == 'services':
            files = job.files.filter(status=ImportJobFile.Status.COMPLETED)
            suffix = 'servicos'
        elif category == 'services-excel':
            files = job.files.filter(
                status=ImportJobFile.Status.COMPLETED, result__isnull=False
            ).select_related('result')
            if not files.exists():
                return Response(
                    {'detail': 'Nenhum dado disponível para exportar.'},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return self._build_excel(job, files)
        else:
            files = job.files.filter(
                models.Q(
                    status=ImportJobFile.Status.COMPLETED, export_to_others=True
                )
                | ~models.Q(status=ImportJobFile.Status.COMPLETED)
            )
            suffix = 'outros'

        if not files.exists():
            return Response(
                {'detail': 'Nenhum arquivo disponível para download.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
            for job_file in files:
                if not job_file.stored_file:
                    continue
                with job_file.stored_file.open('rb') as handler:
                    archive.writestr(job_file.file_name, handler.read())
        buffer.seek(0)
        filename = f'job-{str(job.id)[:8]}-{suffix}.zip'
        response = HttpResponse(buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename=\"{filename}\"'
        return response

    def _build_excel(self, job: ImportJob, files) -> HttpResponse:
        wb = Workbook()
        ws = wb.active
        ws.title = 'Notas de serviço'
        company_name = (job.options or {}).get('companyName', '')
        headers = [
            'Arquivo',
            'Código empresa',
            'Razão social',
            'Município',
            'Número',
            'Chave de acesso',
            'Competência',
            'Competência período',
            'Emissão',
            'DPS número',
            'DPS série',
            'DPS emissão',
            'Emitente',
            'CNPJ emitente',
            'Inscrição emitente',
            'Telefone emitente',
            'Email emitente',
            'Endereço emitente',
            'CEP emitente',
            'Optante Simples',
            'Regime especial',
            'Tomador',
            'CNPJ tomador',
            'Telefone tomador',
            'Email tomador',
            'Endereço tomador',
            'CEP tomador',
            'Serviço código nacional',
            'Serviço código municipal',
            'Local do serviço',
            'Descrição do serviço',
            'Valor do serviço',
            'Base de cálculo',
            'Alíquota ISS',
            'Valor ISS',
            'ISS retido',
            'Regime municipal',
            'Cidade de incidência',
            'Tributação municipal',
            'Comentário de impostos',
            'Comentário federal',
            'Totais valor serviço',
            'Totais ISS retido',
            'Totais valor retido',
            'Totais valor líquido',
            'Info complementar',
            'Criado em',
            'Atualizado em',
        ]
        ws.append(headers)

        def _dt(value):
            return value.isoformat() if value else ''

        def _num(value):
            return float(value) if value not in (None, '') else ''

        for job_file in files:
            nf = job_file.result
            ws.append(
                [
                    nf.file_name,
                    nf.company_code,
                    company_name,
                    nf.municipality,
                    nf.number,
                    nf.access_key,
                    _dt(nf.competence),
                    nf.competence_period,
                    _dt(nf.emission_datetime),
                    nf.dps_number,
                    nf.dps_series,
                    _dt(nf.dps_emission_datetime),
                    nf.emitter_name,
                    nf.emitter_cnpj,
                    nf.emitter_inscription,
                    nf.emitter_phone,
                    nf.emitter_email,
                    nf.emitter_address,
                    nf.emitter_zipcode,
                    bool(nf.emitter_optante_simples),
                    nf.emitter_regime_especial,
                    nf.taker_name,
                    nf.taker_cnpj,
                    nf.taker_phone,
                    nf.taker_email,
                    nf.taker_address,
                    nf.taker_zipcode,
                    nf.service_national_code,
                    nf.service_municipal_code,
                    nf.service_location,
                    nf.service_description,
                    _num(nf.service_value),
                    _num(nf.service_base_calculo),
                    _num(nf.service_iss_rate),
                    _num(nf.service_iss_value),
                    bool(nf.service_iss_retido),
                    nf.municipal_regime,
                    nf.municipal_incidence_city,
                    nf.municipal_taxation,
                    nf.tax_comment,
                    nf.federal_tax_comment,
                    _num(nf.totals_service_value),
                    bool(nf.totals_iss_retido),
                    _num(nf.totals_retained_value),
                    _num(nf.totals_net_value),
                    nf.complementary_info,
                    _dt(nf.created_at),
                    _dt(nf.updated_at),
                ]
            )

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        filename = f'job-{str(job.id)[:8]}-servicos.xlsx'
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f'attachment; filename=\"{filename}\"'
        return response


class JobFileBuilder:
    def prepare_job_files(self, job: ImportJob, descriptor: dict) -> list[ImportJobFile]:
        file_name = descriptor['fileName']
        upload_token = descriptor['uploadToken']
        is_zip = file_name.lower().endswith('.zip')
        if not is_zip:
            job_file = ImportJobFile(
                job=job,
                file_name=file_name,
                file_size=descriptor.get('size') or 0,
            )
            job_file.stored_file.name = upload_token
            return [job_file]
        return self._expand_zip(job, file_name, upload_token)

    def _expand_zip(self, job: ImportJob, original_name: str, upload_token: str) -> list[ImportJobFile]:
        extracted_files: list[ImportJobFile] = []
        try:
            with default_storage.open(upload_token, 'rb') as uploaded_file:
                with zipfile.ZipFile(uploaded_file) as archive:
                    for member in archive.namelist():
                        if member.endswith('/'):
                            continue
                        if not member.lower().endswith('.pdf'):
                            continue
                        data = archive.read(member)
                        extracted_name = Path(member).name
                        content = ContentFile(data)
                        storage_name = self._generate_storage_name(extracted_name)
                        saved_name = default_storage.save(storage_name, content)
                        job_file = ImportJobFile(
                            job=job,
                            file_name=extracted_name,
                            file_size=len(data),
                        )
                        job_file.stored_file.name = saved_name
                        extracted_files.append(job_file)
        except zipfile.BadZipFile as exc:
            raise ValidationError({'detail': f'Arquivo ZIP inválido ({original_name}).'}) from exc
        finally:
            try:
                default_storage.delete(upload_token)
            except Exception:  # pragma: no cover - limpeza best-effort
                pass

        if not extracted_files:
            raise ValidationError(
                {'detail': f'O arquivo ZIP {original_name} não contém PDFs válidos.'}
            )
        return extracted_files

    @staticmethod
    def _generate_storage_name(filename: str) -> str:
        today_path = timezone.now().strftime('%Y/%m/%d')
        safe_name = Path(filename).name
        return str(Path('nfse/uploads') / today_path / f'{uuid.uuid4()}_{safe_name}')
