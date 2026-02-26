from rest_framework import serializers

from .models import VwDctfwebPosicaoGeral


class DctfwebPosicaoGeralSerializer(serializers.ModelSerializer):
    saldo_pagar_formatado = serializers.SerializerMethodField()

    class Meta:
        model = VwDctfwebPosicaoGeral
        fields = [
            'cod_folha',
            'razao_social',
            'cnpj_original',
            'inicio_contrato',
            'termino_contrato',
            'sistema',
            'origem',
            'classificacao2',
            'tipo',
            'situacao',
            'saldo_pagar',
            'saldo_pagar_formatado',
        ]

    def get_saldo_pagar_formatado(self, obj: VwDctfwebPosicaoGeral) -> str:
        return obj.saldo_pagar_formatado
