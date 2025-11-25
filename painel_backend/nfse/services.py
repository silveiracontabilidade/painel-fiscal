import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, Optional

import pdfplumber
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
from django.utils import timezone as django_timezone
from openai import OpenAI, OpenAIError

from .models import ReinfNFS

logger = logging.getLogger(__name__)


@dataclass
class NFSePayload:
    file_name: str
    municipality: str
    access_key: str
    number: str
    competence: Optional[str] = None
    emission_datetime: Optional[str] = None
    dps_number: Optional[str] = None
    dps_series: Optional[str] = None
    dps_emission_datetime: Optional[str] = None
    emitter_name: str = ''
    emitter_cnpj: str = ''
    emitter_inscription: Optional[str] = None
    emitter_phone: Optional[str] = None
    emitter_email: Optional[str] = None
    emitter_address: Optional[str] = None
    emitter_zipcode: Optional[str] = None
    emitter_optante_simples: Optional[bool] = None
    emitter_regime_especial: Optional[str] = None
    taker_name: str = ''
    taker_cnpj: Optional[str] = None
    taker_phone: Optional[str] = None
    taker_email: Optional[str] = None
    taker_address: Optional[str] = None
    taker_zipcode: Optional[str] = None
    service_national_code: Optional[str] = None
    service_municipal_code: Optional[str] = None
    service_location: Optional[str] = None
    service_description: Optional[str] = None
    service_value: Optional[Any] = None
    service_base_calculo: Optional[Any] = None
    service_iss_rate: Optional[Any] = None
    service_iss_value: Optional[Any] = None
    service_iss_retido: Optional[bool] = None
    municipal_regime: Optional[str] = None
    municipal_incidence_city: Optional[str] = None
    municipal_taxation: Optional[str] = None
    tax_comment: Optional[str] = None
    federal_tax_comment: Optional[str] = None
    totals_service_value: Optional[Any] = None
    totals_iss_retido: Optional[bool] = None
    totals_retained_value: Optional[Any] = None
    totals_net_value: Optional[Any] = None
    complementary_info: Optional[str] = None


class NFSeImporter:
    """Reads PDF files and extracts NFSe data via OCR + GPT, persisting to the database."""

    MAX_PROMPT_CHARS = 10000
    SERVICE_KEYWORDS = [
        'nota fiscal de serviços',
        'nota fiscal de serviço',
        'nota fiscal de serviços eletrônica',
        'nfse',
        'nfs-e',
        'dps',
        'prestador do serviço',
        'tomador do serviço',
        'tomador de serviço',
        'iss',
        'issqn',
        'município de incidência',
        'regime especial',
        'código tributação',
        'serviço prestado',
    ]
    SERVICE_MIN_MATCHES = 2
    RELEVANT_KEYWORDS = [
        'dados gerais',
        'chave de acesso',
        'competência',
        'data/hora',
        'dados da dps',
        'emitente',
        'prestador',
        'tomador',
        'serviço prestado',
        'tributação',
        'iss',
        'pis',
        'cofins',
        'dps',
        'regime especial',
        'reten',
        'valor do serviço',
        'informações complementares',
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        ocr_language: Optional[str] = None,
        company_code: Optional[str] = None,
        competence_period: Optional[str] = None,
    ):
        if not api_key:
            api_key = os.getenv('OPENAI_API_KEY', 'ollama')

        base_url = base_url or os.getenv('OPENAI_BASE_URL')
        if base_url:
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            self.client = OpenAI(api_key=api_key)

        env_model = os.getenv('OPENAI_MODEL')
        default_candidates = ['gpt-4o-mini-fast', 'gpt-4o-mini', 'gpt-3.5-turbo']
        if base_url:
            default_candidates.insert(0, 'llama3.2')
            default_candidates.insert(1, 'mistral:7b-instruct')
        model_candidates = [model, env_model, *default_candidates]
        unique_candidates = []
        for candidate in model_candidates:
            if candidate and candidate not in unique_candidates:
                unique_candidates.append(candidate)
        self.model_candidates = unique_candidates or ['gpt-4o-mini']
        self.model = self.model_candidates[0]
        self.company_code = (company_code or '').strip()
        self.competence_period = (competence_period or '').strip()
        self.ocr_language = ocr_language or os.getenv('NFSE_OCR_LANGUAGE', 'por')
        self.logger = logger.getChild(self.__class__.__name__)

    def process_file(
        self, pdf_path: str, pre_extracted: Optional[Dict[str, Any]] = None
    ) -> ReinfNFS:
        start = perf_counter()
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(pdf_path)

        if pre_extracted:
            text = pre_extracted['text']
            text_time = pre_extracted.get('time', 0)
        else:
            text_start = perf_counter()
            text = self.extract_text(pdf_path)
            text_time = perf_counter() - text_start

        prompt_start = perf_counter()
        payload = self._query_chatgpt(text, pdf_path.name)
        prompt_time = perf_counter() - prompt_start

        persist_start = perf_counter()
        nfse = self._persist_payload(payload)
        persist_time = perf_counter() - persist_start

        total_time = perf_counter() - start

        message = (
            f'Terminou {pdf_path.name} | OCR: {text_time:.2f}s | '
            f'OpenAI: {prompt_time:.2f}s | Persistência: {persist_time:.2f}s | '
            f'Total: {total_time:.2f}s'
        )
        self.logger.info(message)
        print(message)
        return nfse

    def extract_text(self, pdf_path: Path) -> str:
        text_chunks = []
        with pdfplumber.open(pdf_path) as pdf:
            for idx, page in enumerate(pdf.pages, start=1):
                try:
                    page_text = page.extract_text() or ''
                except Exception as exc:  # pragma: no cover - PDF parsing edge case
                    self.logger.warning(
                        'Falha ao extrair texto bruto (%s): %s', pdf_path.name, exc
                    )
                    page_text = ''
                normalized = self._normalize_text(page_text)
                if normalized:
                    text_chunks.append(normalized)
                    continue

                self.logger.info(
                    'Executando OCR no arquivo %s página %s.', pdf_path.name, idx
                )
                print(f'OCR necessário para {pdf_path.name} (página {idx})')
                image = self._page_to_image(pdf_path, idx, page)
                ocr_text = pytesseract.image_to_string(image, lang=self.ocr_language)
                normalized_ocr = self._normalize_text(ocr_text)
                if normalized_ocr:
                    text_chunks.append(normalized_ocr)

        combined = '\n'.join(text_chunks)
        return combined

    def _page_to_image(self, pdf_path: Path, page_number: int, page) -> Image.Image:
        try:
            return page.to_image(resolution=300).original
        except Exception:  # pragma: no cover - fallback path
            images = convert_from_path(
                str(pdf_path), first_page=page_number, last_page=page_number
            )
            return images[0]

    def _query_chatgpt(self, text: str, file_name: str) -> Dict[str, Any]:
        clean_text = self._prepare_prompt_text(text)
        prompt = (
            "Você é um assistente que lê o texto bruto de uma NFSe em português e devolve um JSON "
            "com o seguinte formato (obrigatoriamente em JSON válido e com datas ISO):\n"
            "{\n"
            '  "file_name": "...",\n'
            '  "municipality": "...",\n'
            '  "access_key": "...",\n'
            '  "number": "...",\n'
            '  "competence": "AAAA-MM-DD",\n'
            '  "emission_datetime": "AAAA-MM-DDTHH:MM:SS",\n'
            '  "dps_number": "...",\n'
            '  "dps_series": "...",\n'
            '  "dps_emission_datetime": "AAAA-MM-DDTHH:MM:SS",\n'
            '  "emitter_name": "...",\n'
            '  "emitter_cnpj": "...",\n'
            '  "emitter_inscription": "...",\n'
            '  "emitter_phone": "...",\n'
            '  "emitter_email": "...",\n'
            '  "emitter_address": "...",\n'
            '  "emitter_zipcode": "...",\n'
            '  "emitter_optante_simples": true/false,\n'
            '  "emitter_regime_especial": "...",\n'
            '  "taker_name": "...",\n'
            '  "taker_cnpj": "...",\n'
            '  "taker_phone": "...",\n'
            '  "taker_email": "...",\n'
            '  "taker_address": "...",\n'
            '  "taker_zipcode": "...",\n'
            '  "service_national_code": "...",\n'
            '  "service_municipal_code": "...",\n'
            '  "service_location": "...",\n'
            '  "service_description": "...",\n'
            '  "service_value": number,\n'
            '  "service_base_calculo": number,\n'
            '  "service_iss_rate": number,\n'
            '  "service_iss_value": number,\n'
            '  "service_iss_retido": true/false,\n'
            '  "municipal_regime": "...",\n'
            '  "municipal_incidence_city": "...",\n'
            '  "municipal_taxation": "...",\n'
            '  "tax_comment": "...",\n'
            '  "federal_tax_comment": "...",\n'
            '  "totals_service_value": number,\n'
            '  "totals_iss_retido": true/false,\n'
            '  "totals_retained_value": number,\n'
            '  "totals_net_value": number,\n'
            '  "complementary_info": "..."\n'
            "}\n"
            "Retorne apenas o JSON, sem comentários. Texto da nota:\n"
            f"Arquivo: {file_name}\n{clean_text}"
        )

        response = self._request_completion(prompt)
        content = response.choices[0].message.content
        return json.loads(content)

    def _persist_payload(self, payload_dict: Dict[str, Any]) -> ReinfNFS:
        payload = NFSePayload(**payload_dict)
        defaults = {
            'file_name': payload.file_name,
            'municipality': payload.municipality or '',
            'company_code': self.company_code,
            'number': payload.number,
            'competence': self._parse_date(payload.competence),
            'competence_period': self.competence_period,
            'emission_datetime': self._parse_datetime(payload.emission_datetime),
            'dps_number': payload.dps_number or '',
            'dps_series': payload.dps_series or '',
            'dps_emission_datetime': self._parse_datetime(payload.dps_emission_datetime),
            'emitter_name': payload.emitter_name,
            'emitter_cnpj': payload.emitter_cnpj,
            'emitter_inscription': payload.emitter_inscription or '',
            'emitter_phone': payload.emitter_phone or '',
            'emitter_email': payload.emitter_email or '',
            'emitter_address': payload.emitter_address or '',
            'emitter_zipcode': payload.emitter_zipcode or '',
            'emitter_optante_simples': bool(payload.emitter_optante_simples),
            'emitter_regime_especial': payload.emitter_regime_especial or '',
            'taker_name': payload.taker_name or '',
            'taker_cnpj': payload.taker_cnpj or '',
            'taker_phone': payload.taker_phone or '',
            'taker_email': payload.taker_email or '',
            'taker_address': payload.taker_address or '',
            'taker_zipcode': payload.taker_zipcode or '',
            'service_national_code': payload.service_national_code or '',
            'service_municipal_code': payload.service_municipal_code or '',
            'service_location': payload.service_location or '',
            'service_description': payload.service_description or '',
            'service_value': self._to_decimal(payload.service_value),
            'service_base_calculo': self._to_decimal(payload.service_base_calculo),
            'service_iss_rate': self._to_decimal(payload.service_iss_rate),
            'service_iss_value': self._to_decimal(payload.service_iss_value),
            'service_iss_retido': bool(payload.service_iss_retido),
            'municipal_regime': payload.municipal_regime or '',
            'municipal_incidence_city': payload.municipal_incidence_city or '',
            'municipal_taxation': payload.municipal_taxation or '',
            'tax_comment': payload.tax_comment or '',
            'federal_tax_comment': payload.federal_tax_comment or '',
            'totals_service_value': self._to_decimal(payload.totals_service_value),
            'totals_iss_retido': bool(payload.totals_iss_retido),
            'totals_retained_value': self._to_decimal(payload.totals_retained_value),
            'totals_net_value': self._to_decimal(payload.totals_net_value),
            'complementary_info': payload.complementary_info or '',
        }
        nfse, _ = ReinfNFS.objects.update_or_create(
            access_key=payload.access_key,
            defaults=defaults,
        )
        return nfse

    @staticmethod
    def _parse_date(value: Optional[str]):
        if not value:
            return None
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            return None

    @staticmethod
    def _parse_datetime(value: Optional[str]):
        if not value:
            return None
        try:
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                return django_timezone.make_aware(dt)
            return dt.astimezone(django_timezone.get_current_timezone())
        except ValueError:
            return None

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

    def _prepare_prompt_text(self, text: str) -> str:
        normalized = self._normalize_text(text)
        reduced = self._filter_relevant_content(normalized)
        if len(reduced) > self.MAX_PROMPT_CHARS:
            return reduced[: self.MAX_PROMPT_CHARS]
        return reduced

    def is_service_invoice(self, text: str) -> bool:
        normalized = self._normalize_text(text).lower()
        matches = sum(1 for keyword in self.SERVICE_KEYWORDS if keyword in normalized)
        return matches >= self.SERVICE_MIN_MATCHES

    def _request_completion(self, prompt: str):
        messages = [
            {'role': 'system', 'content': 'Você extrai dados estruturados de notas fiscais do Brasil.'},
            {'role': 'user', 'content': prompt},
        ]
        last_error = None
        for candidate in self.model_candidates:
            try:
                response = self.client.chat.completions.create(
                    model=candidate,
                    temperature=0,
                    messages=messages,
                )
                if candidate != self.model:
                    self.logger.warning('Modelo trocado para %s após fallback.', candidate)
                    self.model = candidate
                return response
            except OpenAIError as exc:  # pragma: no cover - depends on network
                last_error = exc
                if self._is_invalid_api_key(exc):
                    raise RuntimeError(
                        'Chave da OpenAI inválida. Atualize a variável OPENAI_API_KEY ou configure o endpoint customizado.'
                    )
                if not self._is_model_not_found(exc):
                    raise
                self.logger.warning(
                    'Modelo %s indisponível (%s). Tentando próximo candidato.',
                    candidate,
                    getattr(exc, 'message', str(exc)),
                )
                continue
        if last_error:
            raise last_error
        raise RuntimeError('Nenhum modelo disponível para a requisição.')

    @staticmethod
    def _is_model_not_found(exc: Exception) -> bool:
        code = getattr(exc, 'code', None)
        if code == 'model_not_found':
            return True
        message = (getattr(exc, 'message', None) or str(exc)).lower()
        return 'model_not_found' in message or 'does not exist' in message

    @staticmethod
    def _is_invalid_api_key(exc: Exception) -> bool:
        code = getattr(exc, 'code', None)
        if code == 'invalid_api_key':
            return True
        message = (getattr(exc, 'message', None) or str(exc)).lower()
        return 'invalid api key' in message or 'incorrect api key' in message

    def _filter_relevant_content(self, text: str) -> str:
        lines = text.split('\n')
        relevant_indices = set()
        total_lines = len(lines)
        for idx, line in enumerate(lines):
            lower_line = line.lower()
            if any(keyword in lower_line for keyword in self.RELEVANT_KEYWORDS):
                start = max(0, idx - 2)
                end = min(total_lines, idx + 3)
                for i in range(start, end):
                    relevant_indices.add(i)

        if not relevant_indices:
            return text

        ordered_lines = [lines[i] for i in sorted(relevant_indices)]
        deduped_lines = []
        seen = set()
        for line in ordered_lines:
            if line not in seen:
                deduped_lines.append(line)
                seen.add(line)

        reduced_text = '\n'.join(deduped_lines)
        if len(reduced_text) < len(text) * 0.6:
            return reduced_text
        return text

    @staticmethod
    def _to_decimal(value: Optional[Any]) -> Decimal:
        if value in (None, ''):
            return Decimal('0')
        return Decimal(str(value))
