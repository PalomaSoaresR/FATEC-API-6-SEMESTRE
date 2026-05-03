import logging
from functools import lru_cache
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

from backend.database import get_mongo_sync_db
from backend.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

WAIT_COUNTDOWN = 30
MAX_WAIT_RETRIES = 60

_COR_SAM = '#1565C0'


@lru_cache(maxsize=None)
def _output_dir() -> Path:
    path = Path(__file__).resolve().parent.parent.parent / 'output' / 'images'
    path.mkdir(parents=True, exist_ok=True)
    return path


@celery_app.task(
    bind=True, max_retries=MAX_WAIT_RETRIES, name='etl.render_sam'
)
def task_render_sam(
    self, job_id: str, distribuidora_id: str, sig_agente: str, ano: int
) -> dict:
    logger.info('[task_render_sam] Inicio. job_id=%s', job_id)

    db = get_mongo_sync_db()
    doc = db['sam_resultados'].find_one(
        {'job_id': job_id, 'distribuidora_id': distribuidora_id},
        {'_id': 0},
    )

    if not doc:
        raise self.retry(countdown=WAIT_COUNTDOWN)

    records = doc.get('records', [])
    if not records:
        logger.warning(
            '[task_render_sam] Nenhum registro disponível. job_id=%s', job_id
        )
        return {'job_id': job_id, 'status': 'skipped', 'reason': 'no_records'}

    conjuntos = [r.get('nome') or r.get('conjunto', '') for r in records]
    sam_vals  = np.array([r.get('sam_km', 0.0) for r in records])

    x = np.arange(len(conjuntos))

    fig_width = max(14, len(conjuntos) * 0.85)
    fig, ax = plt.subplots(figsize=(fig_width, 7))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')

    bars = ax.bar(x, sam_vals, width=0.55, color=_COR_SAM, zorder=3)

    # Valor no topo de cada barra
    for bar, val in zip(bars, sam_vals):
        if val > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + sam_vals.max() * 0.01,
                f'{val:.3f}',
                ha='center', va='bottom',
                fontsize=7, color='#333333',
            )

    ax.set_xticks(x)
    ax.set_xticklabels(conjuntos, rotation=45, ha='right', fontsize=8, color='#333333')
    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda v, _: f'{v:.2f}')
    )
    ax.tick_params(axis='y', colors='#555555', labelsize=8)
    ax.set_ylabel('SAM (km)', fontsize=9, color='#555555')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#cccccc')
    ax.spines['bottom'].set_color('#cccccc')
    ax.grid(axis='y', color='#eeeeee', linewidth=0.8, zorder=0)

    ax.set_title(
        f'Gráfico de todos os Conjuntos (SAM)\n'
        f'{sig_agente} |  Ano: {ano}',
        fontsize=11,
        color='#222222',
        pad=14,
        loc='left',
    )

    plt.tight_layout()

    out_path = _output_dir() / f'sam_{sig_agente}_{ano}.png'
    plt.savefig(out_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)

    logger.info(
        '[task_render_sam] Concluida. job_id=%s path=%s', job_id, out_path
    )
    return {'job_id': job_id, 'status': 'done', 'path': str(out_path)}