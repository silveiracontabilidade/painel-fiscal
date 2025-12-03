import logging
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional

import pdfplumber
import pytesseract
from PIL import Image
from django.utils import timezone as django_timezone
from pdf2image import convert_from_path

from .models import ReinfNFS

logger = logging.getLogger(__name__)


class RegexNFSeImporter:
    """Extracts NFSe data with heuristics/regex only (sem OpenAI)."""

    SERVICE_KEYWORDS = [
        'nota fiscal de serviços',
        'nota fiscal de serviço',
        'nota fiscal de serviços eletrônica',
        'nfse',
        'nfs-e',
        'prestador do serviço',
        'tomador do serviço',
        'iss',
        'issqn',
        'município de incidência',
        'regime especial',
        'código tributação',
        'serviço prestado',
    ]
    SERVICE_MIN_MATCHES = 2
    EXCLUDED_PATTERNS = [
        r'\bnota fiscal de fatura\b',
        r'\bfatura fiscal\b',
        r'\bfatura\b',
    ]
    BILLING_KEYWORDS = [
        'fatura',
        'faturamento',
        'boleto',
        'vencimento',
        'código de barras',
        'linha digitável',
    ]

    def __init__(self):
        self.logger = logger.getChild(self.__class__.__name__)

    def process_file(self, pdf_path: Path, text: Optional[str] = None) -> ReinfNFS:
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(pdf_path)

        if text is None:
            text = self.extract_text(pdf_path)
        normalized = self._normalize_text(text)

        if not self.is_service_invoice(normalized):
            raise ValueError('Documento não parece ser uma NFSe.')

        payload = self._parse_text(normalized)
        payload['file_name'] = pdf_path.name
        if not payload.get('access_key'):
            payload['access_key'] = self._extract_access_key(normalized, pdf_path.name)
        nfse = self._persist_payload(payload)
        return nfse

    def extract_text(self, pdf_path: Path) -> str:
        text_chunks = []
        with pdfplumber.open(pdf_path) as pdf:
            for idx, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text() or ''
                normalized = self._normalize_text(page_text)
                if normalized:
                    text_chunks.append(normalized)
                    continue

                self.logger.info(
                    'Executando OCR no arquivo %s página %s.', pdf_path.name, idx
                )
                image = self._page_to_image(pdf_path, idx, page)
                ocr_text = pytesseract.image_to_string(image, lang='por')
                normalized_ocr = self._normalize_text(ocr_text)
                if normalized_ocr:
                    text_chunks.append(normalized_ocr)

        return '\n'.join(text_chunks)

    def is_service_invoice(self, text: str) -> bool:
        normalized = self._normalize_text(text).lower()
        matches = sum(1 for keyword in self.SERVICE_KEYWORDS if keyword in normalized)
        if matches >= self.SERVICE_MIN_MATCHES:
            return True
        if any(re.search(pattern, normalized) for pattern in self.EXCLUDED_PATTERNS):
            return False
        return False

    def has_billing_markers(self, text: str) -> bool:
        normalized = self._normalize_text(text).lower()
        if not normalized:
            return False
        return any(keyword in normalized for keyword in self.BILLING_KEYWORDS)

    def _parse_text(self, text: str) -> Dict[str, Any]:
        def search(patterns, flags=re.IGNORECASE):
            for pattern in patterns:
                match = re.search(pattern, text, flags)
                if match:
                    return match.group(1).strip()
            return ''

        def search_block(label: str):
            pattern = (
                label + r'[:\-–]*\s*(.+?)(?:\n\d+\.\s|\n[A-Z][^\n]{0,40}:|$)'
            )
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return self._normalize_text(match.group(1))
            return ''

        def parse_bool(value: str):
            return value.strip().lower().startswith('s')

        data = {
            'municipality': search(
                [
                    r'nfse\s+\d+\s+[—-]\s+([^\n]+)',
                    r'município(?: de incidência)?:\s*([^\n]+)',
                    r'local da prestação:\s*([^\n]+)',
                ]
            ),
            'access_key': re.sub(
                r'\D', '',
                search([r'chave de acesso[:\- ]*([\d\s]+)', r'chave[:\- ]*([\d\s]{30,})'])
            ),
            'number': search([r'Número[:\- ]+([\d\.]+)', r'Número da dps[:\- ]+([\d\.]+)']),
            'competence': search([r'Compet[êe]ncia[:\- ]+(\d{2}/\d{2}/\d{4})']),
            'emission_datetime': search(
                [r'Data/Hora da emissão[:\- ]+(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})']
            ),
            'dps_number': search([r'Número da DPS[:\- ]+([\w\d]+)']),
            'dps_series': search([r'Série da DPS[:\- ]+([\w\d]+)']),
            'dps_emission_datetime': search(
                [
                    r'Data/Hora da emissão da DPS[:\- ]+(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})',
                    r'Data/Hora da emiss[aã]o da DPS[:\- ]+(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})',
                ]
            ),
            'emitter_name': search([r'Raz[aã]o Social[:\- ]+(.+)']),
            'emitter_cnpj': search([r'CNPJ[:\- ]+([\d\./-]+)']),
            'emitter_inscription': search([r'Inscriç[aã]o Municipal[:\- ]+([\w\d]+)']),
            'emitter_phone': search([r'Telefone[:\- ]+([^\n]+)']),
            'emitter_email': search([r'E-mail[:\- ]+([^\s]+)']),
            'emitter_address': search([r'Endere[cç]o[:\- ]+(.+)']),
            'emitter_zipcode': search([r'CEP[:\- ]+([\d\.-]+)']),
            'emitter_optante_simples': search(
                [r'Optante Simples Nacional[:\- ]+([^\n]+)']
            ),
            'emitter_regime_especial': search([r'Regime especial[:\- ]+([^\n]+)']),
            'taker_name': search([r'Nome/Raz[aã]o Social[:\- ]+(.+)']),
            'taker_cnpj': search([r'(?:CPF|CNPJ)[:\- ]+([\d\./-]+)']),
            'taker_phone': search(
                [r'Telefone[:\- ]+([^\n]+)'],
                flags=re.IGNORECASE | re.MULTILINE,
            ),
            'taker_email': search([r'E-mail[:\- ]+([^\s]+)']),
            'taker_address': search([r'Endere[cç]o[:\- ]+(.+)']),
            'taker_zipcode': search([r'CEP[:\- ]+([\d\.-]+)']),
            'service_national_code': search(
                [r'Código Tributação Nacional[:\- ]+([\w\.\-]+)']
            ),
            'service_municipal_code': search(
                [r'Código Tributação Municipal[:\- ]+([\w\.\-]+)']
            ),
            'service_location': search([r'Local da prestação[:\- ]+([^\n]+)']),
            'service_description': search_block('Descrição do serviço'),
            'service_value': search([r'Valor do serviço[:\- ]+R?\$?\s*([\d\.,]+)']),
            'service_base_calculo': search([r'Base de c[aá]lculo ISS[:\- ]+R?\$?\s*([\d\.,]+)']),
            'service_iss_rate': search([r'Alíquota[:\- ]+([\d,\.]+)%']),
            'service_iss_value': search([r'ISS apurado[:\- ]+R?\$?\s*([\d\.,]+)']),
            'service_iss_retido': search([r'ISS\s+retido[:\- ]+([^\n]+)']),
            'municipal_regime': search([r'Regime especial[:\- ]+([^\n]+)']),
            'municipal_incidence_city': search([r'Município de incidência[:\- ]+([^\n]+)']),
            'municipal_taxation': search([r'Tributa[cç][aã]o[:\- ]+([^\n]+)']),
            'tax_comment': search_block('Tributos aproximados'),
            'federal_tax_comment': search_block('Tributa[cç][aã]o Federal'),
            'totals_service_value': search([r'Valor do serviço[:\- ]+R?\$?\s*([\d\.,]+)']),
            'totals_iss_retido': search([r'ISS retido[:\- ]+([^\n]+)']),
            'totals_retained_value': search([r'IRRF.*retidos[:\- ]+R?\$?\s*([\d\.,]+)']),
            'totals_net_value': search([r'Valor Líquido da NFSe[:\- ]+R?\$?\s*([\d\.,]+)']),
            'complementary_info': search_block('Informações Complementares'),
        }

        return data

    def _persist_payload(self, payload: Dict[str, Any]) -> ReinfNFS:
        access_key = payload.get('access_key') or ''
        access_key = re.sub(r'\D', '', access_key)
        if not access_key:
            raise ValueError('Chave de acesso não encontrada para esta NFSe.')

        def parse_date(value):
            if not value:
                return None
            try:
                return datetime.strptime(value, '%d/%m/%Y').date()
            except ValueError:
                return None

        def parse_datetime(value):
            if not value:
                return None
            for fmt in ('%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M'):
                try:
                    dt = datetime.strptime(value, fmt)
                    return django_timezone.make_aware(dt)
                except ValueError:
                    continue
            return None

        def parse_decimal(value):
            if not value:
                return Decimal('0')
            normalized = (
                value.replace('R$', '')
                .replace(' ', '')
                .replace('.', '')
                .replace(',', '.')
            )
            try:
                return Decimal(normalized)
            except Exception:
                return Decimal('0')

        def parse_bool_text(value, default=False):
            if not value:
                return default
            lowered = value.strip().lower()
            if lowered in {'sim', 's', 'yes', 'true'}:
                return True
            if lowered in {'não', 'nao', 'n', 'false'}:
                return False
            return default

        defaults = {
            'file_name': payload['file_name'],
            'municipality': payload.get('municipality', ''),
            'number': payload.get('number', ''),
            'competence': parse_date(payload.get('competence')),
            'emission_datetime': parse_datetime(payload.get('emission_datetime')),
            'dps_number': payload.get('dps_number', ''),
            'dps_series': payload.get('dps_series', ''),
            'dps_emission_datetime': parse_datetime(payload.get('dps_emission_datetime')),
            'emitter_name': payload.get('emitter_name', ''),
            'emitter_cnpj': payload.get('emitter_cnpj', ''),
            'emitter_inscription': payload.get('emitter_inscription', ''),
            'emitter_phone': payload.get('emitter_phone', ''),
            'emitter_email': payload.get('emitter_email', ''),
            'emitter_address': payload.get('emitter_address', ''),
            'emitter_zipcode': payload.get('emitter_zipcode', ''),
            'emitter_optante_simples': parse_bool_text(
                payload.get('emitter_optante_simples'), default=False
            ),
            'emitter_regime_especial': payload.get('emitter_regime_especial', ''),
            'taker_name': payload.get('taker_name', ''),
            'taker_cnpj': payload.get('taker_cnpj', ''),
            'taker_phone': payload.get('taker_phone', ''),
            'taker_email': payload.get('taker_email', ''),
            'taker_address': payload.get('taker_address', ''),
            'taker_zipcode': payload.get('taker_zipcode', ''),
            'service_national_code': payload.get('service_national_code', ''),
            'service_municipal_code': payload.get('service_municipal_code', ''),
            'service_location': payload.get('service_location', ''),
            'service_description': payload.get('service_description', ''),
            'service_value': parse_decimal(payload.get('service_value')),
            'service_base_calculo': parse_decimal(payload.get('service_base_calculo')),
            'service_iss_rate': parse_decimal(payload.get('service_iss_rate')),
            'service_iss_value': parse_decimal(payload.get('service_iss_value')),
            'service_iss_retido': parse_bool_text(
                payload.get('service_iss_retido'), default=False
            ),
            'municipal_regime': payload.get('municipal_regime', ''),
            'municipal_incidence_city': payload.get('municipal_incidence_city', ''),
            'municipal_taxation': payload.get('municipal_taxation', ''),
            'tax_comment': payload.get('tax_comment', ''),
            'federal_tax_comment': payload.get('federal_tax_comment', ''),
            'totals_service_value': parse_decimal(payload.get('totals_service_value')),
            'totals_iss_retido': parse_bool_text(
                payload.get('totals_iss_retido'), default=False
            ),
            'totals_retained_value': parse_decimal(payload.get('totals_retained_value')),
            'totals_net_value': parse_decimal(payload.get('totals_net_value')),
            'complementary_info': payload.get('complementary_info', ''),
        }

        nfse, _ = ReinfNFS.objects.update_or_create(
            access_key=access_key,
            defaults=defaults,
        )
        return nfse

    @staticmethod
    def _normalize_text(text: Optional[str]) -> str:
        if not text:
            return ''
        text = text.replace('\r', '\n')
        cleaned_lines = []
        for line in text.splitlines():
            normalized_line = re.sub(r'\s+', ' ', line).strip()
            if normalized_line:
                cleaned_lines.append(normalized_line)
        return '\n'.join(cleaned_lines)

    @staticmethod
    def _page_to_image(pdf_path: Path, page_number: int, page) -> Image.Image:
        try:
            return page.to_image(resolution=300).original
        except Exception:  # pragma: no cover
            images = convert_from_path(
                str(pdf_path), first_page=page_number, last_page=page_number
            )
            return images[0]

    def _extract_access_key(self, text: str, file_name: str) -> str:
        candidates = re.findall(r'\d{30,}', text)
        if not candidates:
            name_digits = re.findall(r'\d+', file_name)
            candidates = [digits for digits in name_digits if len(digits) >= 20]

        if candidates:
            candidates.sort(key=len, reverse=True)
            return candidates[0][:44]

        raise ValueError(
            'Chave de acesso não encontrada para esta NFSe (nem no texto nem no nome do arquivo).'
        )
