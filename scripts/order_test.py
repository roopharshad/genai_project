"""Compare stage orders on a page with ground truth: CER/WER per variant."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if __name__ == "__main__":
    import torch  # noqa: F401
    from PIL import Image
    from backend.services import docres_service as d, enhance_service as e, ocr_service as o, paper_restore_service as p

    f = sys.argv[1] if len(sys.argv) > 1 else "samples/faded_document.jpg"
    gt = (Path("samples/gt") / (Path(f).stem + ".txt")).read_text(encoding="utf-8")
    pre, _ = e.page_crop(Image.open(f).convert("RGB"))
    paper_out, _ = p.restore(pre, "white")
    variants = {
        "original": pre,
        "paper only": paper_out,
        "docres appearance (raw)": d.restore(pre, "appearance")[0],
        "docres end2end (raw)": d.restore(pre, "end2end")[0],
        "paper -> docres appearance": d.restore(paper_out, "appearance")[0],
    }
    variants["docres appearance -> paper"] = p.restore(variants["docres appearance (raw)"], "white")[0]
    for k in list(variants)[:2]:
        variants.pop(k)
    variants.pop("docres end2end (raw)")
    variants.pop("paper -> docres appearance")
    for name, im in variants.items():
        t = o.joined(o.read(im))
        print(f"{name:28} CER {o.cer(gt, t):.4f}  WER {o.wer(gt, t):.4f}", flush=True)
