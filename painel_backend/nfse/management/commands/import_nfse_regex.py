import shutil
from pathlib import Path
from time import perf_counter

from django.core.management.base import BaseCommand, CommandError

from nfse.regex_importer import RegexNFSeImporter


class Command(BaseCommand):
    help = 'Importa NFSe usando apenas regex, sem chamadas à API da OpenAI.'

    def add_arguments(self, parser):
        parser.add_argument(
            'input_path',
            help='Arquivo PDF ou pasta contendo PDFs de NFSe.',
        )

    def handle(self, *args, **options):
        input_path = Path(options['input_path'])
        if not input_path.exists():
            raise CommandError(f'Caminho não encontrado: {input_path}')

        importer = RegexNFSeImporter()
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
                self._process(importer, pdf_path)
        else:
            self._process(importer, input_path)

    def _process(self, importer: RegexNFSeImporter, pdf_path: Path):
        start = perf_counter()
        try:
            text = importer.extract_text(pdf_path)

            if not importer.is_service_invoice(text):
                self.stdout.write(
                    self.style.WARNING(f'Ignorando (não é NFSe): {pdf_path.name}')
                )
                self._move_file(pdf_path, self.other_dir)
                return

            nfse = importer.process_file(pdf_path, text=text)
            elapsed = perf_counter() - start
            self.stdout.write(
                self.style.SUCCESS(
                    f'NFSe (regex) importada: {nfse.number or nfse.access_key} '
                    f'- {pdf_path.name} ({elapsed:.2f}s)'
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
