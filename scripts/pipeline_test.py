"""Run the full document pipeline on samples, print timings, plan and quality."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if __name__ == "__main__":
    import torch  # noqa: F401  (torch before paddle, as in the server)
    from PIL import Image
    from backend.services import document_pipeline

    files = sys.argv[1:] or ["samples/faded_document.jpg"]
    for f in files:
        gt = Path("samples/gt") / (Path(f).stem + ".txt")
        steps = []
        t = time.time()
        out, rep = document_pipeline.run(Image.open(f), Path("samples/pipeline_eval") / Path(f).stem, steps,
                                         gt.read_text(encoding="utf-8") if gt.exists() else None)
        print(f"== {Path(f).name}: {time.time() - t:.1f}s timings={rep['timings']}")
        for s in steps:
            print("  -", s)
        print("  chosen:", rep.get("chosen_stage"), "final quality:", rep.get("final_quality"))
        if rep.get("ground_truth"):
            print("  CER/WER:", rep["ground_truth"])
