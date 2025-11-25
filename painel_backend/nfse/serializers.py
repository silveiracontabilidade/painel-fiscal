from typing import Any, Dict

from django.utils import timezone
from rest_framework import serializers

from .models import ImportJob, ImportJobFile, PayrollCompany


class FileDescriptorSerializer(serializers.Serializer):
    fileId = serializers.CharField()
    fileName = serializers.CharField()
    size = serializers.IntegerField()
    uploadToken = serializers.CharField()


class ImportJobOptionsSerializer(serializers.Serializer):
    ocrLanguage = serializers.CharField(required=False, allow_blank=True)
    model = serializers.CharField(required=False, allow_blank=True)
    baseUrl = serializers.CharField(required=False, allow_blank=True)
    companyCode = serializers.CharField(max_length=60)
    companyName = serializers.CharField(required=False, allow_blank=True)
    competencePeriod = serializers.RegexField(
        regex=r'^(0[1-9]|1[0-2])[0-9]{4}$',
        error_messages={'invalid': 'Use o formato MMYYYY.'},
    )

    def validate_companyCode(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError('Informe o código da empresa.')
        return cleaned

    def validate_competencePeriod(self, value: str) -> str:
        return value.strip()

    def validate(self, attrs):
        company_code = (attrs.get('companyCode') or '').strip()
        company = PayrollCompany.objects.filter(
            cod_folha=company_code, matriz__iexact='sim'
        ).first()
        if not company:
            raise serializers.ValidationError(
                {'companyCode': 'Empresa não encontrada na base de DP.'}
            )
        attrs['companyCode'] = company.cod_folha
        attrs['companyName'] = company.razao_social
        return attrs


class ImportJobCreateSerializer(serializers.Serializer):
    files = serializers.ListField(
        child=FileDescriptorSerializer(),
        allow_empty=False,
    )
    options = ImportJobOptionsSerializer()


class ImportJobFileSerializer(serializers.ModelSerializer):
    fileName = serializers.CharField(source='file_name')
    size = serializers.IntegerField(source='file_size')
    downloadUrl = serializers.SerializerMethodField()
    updatedAt = serializers.DateTimeField(source='updated_at')
    createdAt = serializers.DateTimeField(source='created_at')

    class Meta:
        model = ImportJobFile
        fields = [
            'id',
            'fileName',
            'size',
            'status',
            'stage',
            'progress',
            'message',
            'updatedAt',
            'createdAt',
            'downloadUrl',
        ]

    def get_downloadUrl(self, obj: ImportJobFile) -> str | None:
        request = self.context.get('request')
        if not obj.stored_file:
            return None
        try:
            url = obj.stored_file.url
        except ValueError:
            return None
        return request.build_absolute_uri(url) if request else url


class ImportJobSerializer(serializers.ModelSerializer):
    createdAt = serializers.DateTimeField(source='created_at')
    totals = serializers.SerializerMethodField()
    files = ImportJobFileSerializer(many=True, read_only=True)
    displayStatus = serializers.SerializerMethodField()

    class Meta:
        model = ImportJob
        fields = [
            'id',
            'status',
            'displayStatus',
            'createdAt',
            'options',
            'totals',
            'files',
        ]

    def get_totals(self, obj: ImportJob) -> Dict[str, Any]:
        return {
            'totalFiles': obj.totals_total_files,
            'processing': obj.totals_processing,
            'completed': obj.totals_completed,
            'failed': obj.totals_failed,
            'ignored': obj.totals_ignored,
        }

    def get_displayStatus(self, obj: ImportJob) -> str:
        if obj.status == ImportJob.Status.FAILED and obj.totals_completed > 0:
            return 'completed_with_errors'
        return obj.status

    def to_representation(self, instance):
        data = super().to_representation(instance)
        options = data.get('options') or {}
        if options.get('companyCode') and not options.get('companyName'):
            company = PayrollCompany.objects.filter(
                cod_folha=options.get('companyCode'), matriz__iexact='sim'
            ).first()
            if company:
                options['companyName'] = company.razao_social
        data['options'] = options
        return data


class ImportJobDetailSerializer(ImportJobSerializer):
    pass


class ReprocessSerializer(serializers.Serializer):
    fileIds = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
    )
