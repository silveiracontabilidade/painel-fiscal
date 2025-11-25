import threading
from pathlib import Path
from time import perf_counter
from django.core.files.storage import default_storage
from django.db import close_old_connections

from .models import ImportJob, ImportJobFile
from .services import NFSeImporter

JOB_THREADS: dict[str, threading.Thread] = {}
JOB_LOCK = threading.Lock()


def enqueue_job(job_id: str) -> None:
    with JOB_LOCK:
        thread = JOB_THREADS.get(job_id)
        if thread and thread.is_alive():
            return

        thread = threading.Thread(target=_run_job, args=(job_id,), daemon=True)
        JOB_THREADS[job_id] = thread
        thread.start()


def _run_job(job_id: str) -> None:
    close_old_connections()
    try:
        job = ImportJob.objects.get(id=job_id)
    except ImportJob.DoesNotExist:
        return

    options = job.options or {}
    importer = NFSeImporter(
        model=options.get('model'),
        base_url=options.get('baseUrl'),
        ocr_language=options.get('ocrLanguage'),
        company_code=options.get('companyCode'),
        competence_period=options.get('competencePeriod'),
    )

    job.status = ImportJob.Status.PROCESSING
    job.save(update_fields=['status', 'updated_at'])

    files = job.files.filter(status__in=['pending', 'processing']).order_by('created_at')
    for job_file in files:
        _process_file(importer, job, job_file)

    job.refresh_totals()


def _process_file(importer: NFSeImporter, job: ImportJob, job_file: ImportJobFile) -> None:
    job_file.status = ImportJobFile.Status.PROCESSING
    job_file.stage = ImportJobFile.Stage.OCR
    job_file.progress = 5
    job_file.message = ''
    job_file.save(update_fields=['status', 'stage', 'progress', 'message', 'updated_at'])

    try:
        file_path = _resolve_path(job_file.stored_file.name)
        text_start = perf_counter()
        text = importer.extract_text(Path(file_path))
        text_time = perf_counter() - text_start

        if not importer.is_service_invoice(text):
            job_file.status = ImportJobFile.Status.IGNORED
            job_file.stage = ImportJobFile.Stage.DONE
            job_file.progress = 100
            job_file.message = 'Ignorado: não parece ser NF de serviços.'
            job_file.save(
                update_fields=['status', 'stage', 'progress', 'message', 'updated_at']
            )
            job.refresh_totals()
            return

        job_file.stage = ImportJobFile.Stage.AI
        job_file.progress = 65
        job_file.save(update_fields=['stage', 'progress', 'updated_at'])

        nfse = importer.process_file(
            file_path, pre_extracted={'text': text, 'time': text_time}
        )

        job_file.status = ImportJobFile.Status.COMPLETED
        job_file.stage = ImportJobFile.Stage.DONE
        job_file.progress = 100
        job_file.message = 'NF importada com sucesso.'
        job_file.result = nfse
        job_file.save(
            update_fields=[
                'status',
                'stage',
                'progress',
                'message',
                'result',
                'updated_at',
            ]
        )
    except Exception as exc:  # pylint: disable=broad-except
        job_file.status = ImportJobFile.Status.ERROR
        job_file.stage = ImportJobFile.Stage.ERROR
        job_file.progress = 100
        job_file.message = str(exc)
        job_file.save(
            update_fields=['status', 'stage', 'progress', 'message', 'updated_at']
        )
    finally:
        job.refresh_totals()


def _resolve_path(stored_name: str) -> str:
    storage = default_storage
    if hasattr(storage, 'path'):
        return storage.path(stored_name)
    # fallback: download to a temporary file
    tmp_dir = Path('/tmp/nfse_uploads')
    tmp_dir.mkdir(parents=True, exist_ok=True)
    destination = tmp_dir / Path(stored_name).name
    with storage.open(stored_name, 'rb') as source, open(destination, 'wb') as target:
        target.write(source.read())
    return str(destination)
