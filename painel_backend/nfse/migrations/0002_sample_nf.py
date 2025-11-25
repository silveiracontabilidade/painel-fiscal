from datetime import datetime

from django.db import migrations
from django.utils import timezone


def seed_nfse(apps, schema_editor):
    ReinfNFS = apps.get_model('nfse', 'ReinfNFS')

    ReinfNFS.objects.update_or_create(
        access_key='31062001217276558000105250000000110125117518887650',
        defaults={
            'file_name': 'NFe_31062001217276558000105250000000110125117518887650.pdf',
            'municipality': 'Belo Horizonte (BH)',
            'number': '2500000001101',
            'competence': datetime(2025, 11, 4).date(),
            'emission_datetime': timezone.make_aware(datetime(2025, 11, 4, 9, 49, 58)),
            'dps_number': '5848',
            'dps_series': '12025',
            'dps_emission_datetime': timezone.make_aware(datetime(2025, 11, 4, 0, 0, 0)),
            'emitter_name': 'R L PROPAGANDA EMPRESARIAL LTDA',
            'emitter_cnpj': '17.276.558/0001-05',
            'emitter_inscription': '04721680014',
            'emitter_phone': '(31) 3275-0270',
            'emitter_email': 'fan.adm@aneethun.com',
            'emitter_address': 'AVE BARBACENA, 436, sala 601, Barro Preto, Belo Horizonte – MG',
            'emitter_zipcode': '30190-130',
            'emitter_optante_simples': False,
            'emitter_regime_especial': '',
            'taker_name': 'MARIA DAS DORES TEIXEIRA GONCALVES BRUSCO',
            'taker_cnpj': '06.093.198/0001-81',
            'taker_phone': '(19) 3787-5300',
            'taker_email': 'campinas@aneethun.com',
            'taker_address': 'Rua Uirapuru, 783, Jardim São Gonçalo, Campinas – SP',
            'taker_zipcode': '13082-706',
            'service_national_code': '17.06.01',
            'service_municipal_code': '001',
            'service_location': 'Belo Horizonte – MG',
            'service_description': (
                'Comunicação empresarial, promocional e institucional. IR retido na fonte código 8045, '
                'valor R$ 13,13 (pela agência). Informações legais adicionais.'
            ),
            'service_value': 875.00,
            'service_base_calculo': 875.00,
            'service_iss_rate': 3,
            'service_iss_value': 26.25,
            'service_iss_retido': False,
            'municipal_regime': 'Nenhum',
            'municipal_incidence_city': 'Belo Horizonte – MG',
            'municipal_taxation': 'Operação tributável',
            'tax_comment': (
                'Tributos aproximados (Lei 12.741/12): ISS: 3% → R$ 26,25; '
                'PIS: 0,65% → R$ 5,69; COFINS: 3% → R$ 26,25'
            ),
            'federal_tax_comment': 'IRRF, CSLL, PIS e COFINS zerados; sem retenções.',
            'totals_service_value': 875.00,
            'totals_iss_retido': False,
            'totals_retained_value': 0,
            'totals_net_value': 875.00,
            'complementary_info': (
                'Nota gerada com número de série RPS alfanumérico conforme modelo de BH. Nome: RL Propaganda.'
            ),
        },
    )


def unseed_nfse(apps, schema_editor):
    ReinfNFS = apps.get_model('nfse', 'ReinfNFS')
    ReinfNFS.objects.filter(
        access_key='31062001217276558000105250000000110125117518887650'
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('nfse', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_nfse, unseed_nfse),
    ]
