import shutil
from pathlib import Path
from time import perf_counter

from django.core.management.base import BaseCommand, CommandError

from nfse.services import NFSeImporter


class Command(BaseCommand):
    help = 'Importa NFS-e em PDF utilizando OCR + ChatGPT e grava na reinf_NFS.'

    def add_arguments(self, parser):
        parser.add_argument(
            'input_path',
            help='Caminho do arquivo PDF ou de uma pasta contendo PDFs de NFSe.',
        )
        parser.add_argument(
            '--api-key',
            dest='api_key',
            help='Chave da API do ChatGPT/Ollama. Pode ser definida em variáveis de ambiente.',
            required=False,
        )
        parser.add_argument(
            '--model',
            dest='model',
            default=None,
            help='Modelo a ser utilizado (OpenAI ou Ollama).',
        )
        parser.add_argument(
            '--base-url',
            dest='base_url',
            default=None,
            help='Endpoint compatível com OpenAI (ex.: http://127.0.0.1:11434/v1 para Ollama).',
        )

    def handle(self, *args, **options):
        api_key = options.get('api_key') or self._get_api_key()
        if not api_key:
            raise CommandError('Informe --api-key ou configure OPENAI_API_KEY.')

        input_path = Path(options['input_path'])
        if not input_path.exists():
            raise CommandError(f'Caminho não encontrado: {input_path}')

        importer = NFSeImporter(api_key=api_key, model=options['model'], base_url=options['base_url'])
        service_dir, other_dir = self._prepare_output_dirs(input_path)
        self.service_dir = service_dir
        self.other_dir = other_dir
        if input_path.is_dir():
            files = sorted(
                p
                for p in input_path.rglob('*.pdf')
                if service_dir not in p.parents and other_dir not in p.parents
            )
            if not files:
                self.stdout.write(self.style.WARNING('Nenhum PDF encontrado na pasta.'))
                return
            for pdf_path in files:
                self._process_pdf(importer, pdf_path)
        else:
            self._process_pdf(importer, input_path)

    def _get_api_key(self):
        import os

        return os.getenv('OPENAI_API_KEY')

    def _process_pdf(self, importer: NFSeImporter, pdf_path: Path):
        start = perf_counter()
        try:
            text_start = perf_counter()
            text = importer.extract_text(pdf_path)
            text_time = perf_counter() - text_start
            text_payload = {'text': text, 'time': text_time}

            if not importer.is_service_invoice(text):
                self.stdout.write(
                    self.style.WARNING(f'Ignorando (não é serviço): {pdf_path.name}')
                )
                self._move_file(pdf_path, self.other_dir)
                return

            nfse = importer.process_file(str(pdf_path), pre_extracted=text_payload)
            self.stdout.write(
                self.style.SUCCESS(
                    f'NFSe importada: {nfse.number} - {pdf_path.name} '
                    f'({perf_counter() - start:.2f}s)'
                )
            )
            self._move_file(pdf_path, self.service_dir)
        except Exception as exc:  # pylint: disable=broad-except
            self.stderr.write(self.style.ERROR(f'Falha em {pdf_path}: {exc}'))
            self._move_file(pdf_path, self.other_dir)

    def _prepare_output_dirs(self, input_path: Path):
        base_dir = input_path if input_path.is_dir() else input_path.parent
        service_dir = base_dir / 'NF Servicos'
        other_dir = base_dir / 'NF Outros'
        service_dir.mkdir(parents=True, exist_ok=True)
        other_dir.mkdir(parents=True, exist_ok=True)
        return service_dir.resolve(), other_dir.resolve()

    def _move_file(self, file_path: Path, target_dir: Path):
        dest_path = target_dir / file_path.name
        counter = 1
        while dest_path.exists():
            dest_path = target_dir / f'{file_path.stem}_{counter}{file_path.suffix}'
            counter += 1
        try:
            shutil.move(str(file_path), str(dest_path))
        except FileNotFoundError:
            pass
