"""One-shot ML retraining orchestrator.

Runs both deployed trainers (revenue forecast + customer segmentation) and
writes a status JSON so scheduled refreshes can verify success. Run with the
ML Python that has the full stack installed, e.g.:

    conda run -n base python ml/retrain.py

Each trainer re-extracts data from MySQL, retunes/refits, and rewrites the
backend artifacts (model.pkl, metadata.json, feature_stats.json, CSVs).
A backend restart (scripts/refresh_pipeline.ps1) is required afterwards so the
forecast CSV service picks up the new predictions.
"""
import hashlib
import json
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml import train_forecast, train_segmentation


def _sha256(path: Path) -> str:
    if not path.exists():
        return "missing"
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    started = datetime.now().isoformat()
    status = {"started_at": started, "steps": {}}
    ok = True

    for name, trainer in [
        ("forecast", train_forecast),
        ("segmentation", train_segmentation),
    ]:
        t0 = time.time()
        try:
            trainer.main()
            status["steps"][name] = {"status": "ok", "seconds": round(time.time() - t0, 1)}
            print(f"[retrain] {name} model retrained OK")
        except Exception as exc:  # noqa: BLE001 - record any failure and continue
            status["steps"][name] = {"status": "error", "error": repr(exc)}
            print(f"[retrain] {name} retrain FAILED: {exc!r}")
            ok = False

    status["finished_at"] = datetime.now().isoformat()
    status["ok"] = ok
    status["artifacts"] = {
        "forecast_model_sha256": _sha256(PROJECT_ROOT / "backend/app/ml/forecasting/model.pkl"),
        "segmentation_model_sha256": _sha256(PROJECT_ROOT / "backend/app/ml/segmentation/model.pkl"),
    }

    out = PROJECT_ROOT / "ml" / "retrain_status.json"
    out.write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(f"[retrain] status written to {out} (ok={ok})")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
