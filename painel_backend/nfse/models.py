from uuid import uuid4

from django.db import models
from django.db.models import Count, Q


class PayrollCompanyManager(models.Manager):
    """Uses the automacoesdp connection by default."""

    def get_queryset(self):
        return super().get_queryset().using('automacoesdp')


class PayrollCompany(models.Model):
    cod_folha = models.CharField(primary_key=True, max_length=20)
    razao_social = models.CharField(max_length=255)
    matriz = models.CharField(max_length=10, db_column='Matriz', blank=True, null=True)

    objects = PayrollCompanyManager()

    class Meta:
        managed = False
        db_table = 'geral_planilha_gerencial'
        verbose_name = 'Empresa (DP)'
        verbose_name_plural = 'Empresas (DP)'

    def __str__(self) -> str:
        return f'{self.cod_folha} - {self.razao_social}'


class ReinfNFS(models.Model):
    """Stores the structured data extracted from NFSe PDFs."""

    file_name = models.CharField(max_length=255)
    municipality = models.CharField(max_length=120, blank=True)
    company_code = models.CharField(max_length=60, blank=True)
    access_key = models.CharField(max_length=60, unique=True)
    number = models.CharField(max_length=40)
    competence = models.DateField(null=True, blank=True)
    competence_period = models.CharField(max_length=6, blank=True)
    emission_datetime = models.DateTimeField(null=True, blank=True)

    dps_number = models.CharField(max_length=40, blank=True)
    dps_series = models.CharField(max_length=40, blank=True)
    dps_emission_datetime = models.DateTimeField(null=True, blank=True)

    emitter_name = models.CharField(max_length=255)
    emitter_cnpj = models.CharField(max_length=20)
    emitter_inscription = models.CharField(max_length=40, blank=True)
    emitter_phone = models.CharField(max_length=40, blank=True)
    emitter_email = models.EmailField(blank=True)
    emitter_address = models.CharField(max_length=255, blank=True)
    emitter_zipcode = models.CharField(max_length=12, blank=True)
    emitter_optante_simples = models.BooleanField(default=False)
    emitter_regime_especial = models.CharField(max_length=120, blank=True)

    taker_name = models.CharField(max_length=255)
    taker_cnpj = models.CharField(max_length=20, blank=True)
    taker_phone = models.CharField(max_length=40, blank=True)
    taker_email = models.EmailField(blank=True)
    taker_address = models.CharField(max_length=255, blank=True)
    taker_zipcode = models.CharField(max_length=12, blank=True)

    service_national_code = models.CharField(max_length=40, blank=True)
    service_municipal_code = models.CharField(max_length=40, blank=True)
    service_location = models.CharField(max_length=120, blank=True)
    service_description = models.TextField(blank=True)
    service_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    service_base_calculo = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    service_iss_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    service_iss_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    service_iss_retido = models.BooleanField(default=False)
    municipal_regime = models.CharField(max_length=120, blank=True)
    municipal_incidence_city = models.CharField(max_length=120, blank=True)
    municipal_taxation = models.CharField(max_length=500, blank=True)

    tax_comment = models.TextField(blank=True)
    federal_tax_comment = models.TextField(blank=True)

    totals_service_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    totals_iss_retido = models.BooleanField(default=False)
    totals_retained_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    totals_net_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    complementary_info = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reinf_NFS'
        verbose_name = 'NFSe importada'
        verbose_name_plural = 'NFSe importadas'

    def __str__(self) -> str:
        return f'NFSe {self.number} - {self.emitter_name}'


class ImportJob(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendente'
        PROCESSING = 'processing', 'Processando'
        COMPLETED = 'completed', 'Concluído'
        FAILED = 'failed', 'Falhou'

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    options = models.JSONField(default=dict, blank=True)
    totals_total_files = models.PositiveIntegerField(default=0)
    totals_processing = models.PositiveIntegerField(default=0)
    totals_completed = models.PositiveIntegerField(default=0)
    totals_failed = models.PositiveIntegerField(default=0)
    totals_ignored = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'Job {self.id}'

    def refresh_totals(self):
        agg = self.files.aggregate(
            total=Count('id'),
            processing=Count(
                'id',
                filter=Q(status__in=['pending', 'uploading', 'processing']),
            ),
            completed=Count('id', filter=Q(status='completed')),
            failed=Count('id', filter=Q(status='error')),
            ignored=Count('id', filter=Q(status__in=['ignored', 'skipped'])),
        )
        self.totals_total_files = agg.get('total') or 0
        self.totals_processing = agg.get('processing') or 0
        self.totals_completed = agg.get('completed') or 0
        self.totals_failed = agg.get('failed') or 0
        self.totals_ignored = agg.get('ignored') or 0

        if self.totals_total_files == 0:
            self.status = self.Status.PENDING
        elif self.totals_processing > 0:
            self.status = self.Status.PROCESSING
        elif self.totals_failed > 0:
            self.status = self.Status.FAILED
        else:
            self.status = self.Status.COMPLETED

        self.save(
            update_fields=[
                'totals_total_files',
                'totals_processing',
                'totals_completed',
                'totals_failed',
                'totals_ignored',
                'status',
                'updated_at',
            ]
        )


class ImportJobFile(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendente'
        UPLOADING = 'uploading', 'Enviando'
        PROCESSING = 'processing', 'Processando'
        COMPLETED = 'completed', 'Concluído'
        ERROR = 'error', 'Erro'
        IGNORED = 'ignored', 'Ignorado'

    class Stage(models.TextChoices):
        QUEUED = 'queued', 'Fila'
        OCR = 'ocr', 'OCR'
        AI = 'ai', 'LLM'
        PERSISTING = 'persisting', 'Persistindo'
        DONE = 'done', 'Finalizado'
        ERROR = 'error', 'Erro'

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    job = models.ForeignKey(
        ImportJob, related_name='files', on_delete=models.CASCADE, db_index=True
    )
    file_name = models.CharField(max_length=255)
    file_size = models.BigIntegerField(default=0)
    stored_file = models.FileField(upload_to='nfse/uploads/%Y/%m/%d', max_length=500)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    stage = models.CharField(max_length=20, choices=Stage.choices, default=Stage.QUEUED)
    progress = models.PositiveSmallIntegerField(default=0)
    message = models.TextField(blank=True)
    result = models.ForeignKey(
        ReinfNFS, null=True, blank=True, on_delete=models.SET_NULL, related_name='job_files'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self) -> str:
        return f'{self.file_name} ({self.status})'
