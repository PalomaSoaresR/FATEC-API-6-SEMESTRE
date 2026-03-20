import os
from pathlib import Path
import httpx
import zipfile
from backend.tasks.celery_app import celery_app
from celery import Task

DOWNLOAD_DIR = Path(os.getenv('DOWNLOAD_DIR', '/data/downloads/'))

@celery_app.task(bind=True, max_retries=2, default_retry_delay=60, name="etl.download_gdb")
def task_download_gdb(self, job_id: str, url: str) -> dict:
    if not url:
        raise RuntimeError("URL de download não fornecida")

    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = DOWNLOAD_DIR / f"{job_id}.zip"

    try:
        with httpx.stream("GET", url, follow_redirects=True, timeout=300) as r:
            r.raise_for_status()
            with open(zip_path, "wb") as f:
                for chunk in r.iter_bytes(chunk_size=8192):
                    f.write(chunk)

        # Valida ZIP
        if not zipfile.is_zipfile(zip_path):
            zip_path.unlink(missing_ok=True)
            raise RuntimeError("Arquivo baixado não é um ZIP válido")

        # Enfileira próxima task (não executa diretamente)
        self.request.chain = [("etl.extrair_gdb", (job_id, str(zip_path)))]

        return {"job_id": job_id, "zip_path": str(zip_path), "status": "downloaded"}

    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        zip_path.unlink(missing_ok=True)
        raise self.retry(exc=exc)
    except Exception as exc:
        zip_path.unlink(missing_ok=True)
        raise
