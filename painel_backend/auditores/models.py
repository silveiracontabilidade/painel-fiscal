from django.db import models


class VwDctfwebPosicaoGeral(models.Model):
    cod_folha = models.IntegerField(primary_key=True, db_column='Cod_folha')
    razao_social = models.CharField(max_length=255, db_column='Razao_Social')
    cnpj_original = models.CharField(max_length=18, db_column='CNPJ_Original')
    inicio_contrato = models.DateField(db_column='Inicio_Contrato', null=True, blank=True)
    termino_contrato = models.DateField(db_column='Termino_Contrato', null=True, blank=True)
    sistema = models.CharField(max_length=50, db_column='Sistema')
    origem = models.CharField(max_length=50, db_column='origem')
    classificacao2 = models.CharField(max_length=50, db_column='Classificacao2')
    tipo = models.CharField(max_length=50, db_column='tipo')
    situacao = models.CharField(max_length=100, db_column='situacao')
    saldo_pagar = models.DecimalField(max_digits=15, decimal_places=2, db_column='saldo_pagar')

    @property
    def saldo_pagar_formatado(self) -> str:
        if self.saldo_pagar is None:
            return '0,00'
        valor = f"{self.saldo_pagar:,.2f}"
        return valor.replace(',', 'X').replace('.', ',').replace('X', '.')

    class Meta:
        managed = False
        db_table = 'VW_DCTFWEB_posicao_geral'
        app_label = 'auditores'
