"""Run the final enhancement step (enhance + OCR validation + text-safe fallback) on restored pages."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if __name__ == "__main__":
    import torch  # noqa: F401
    from PIL import Image
    from backend.services import enhancement_service as en

    out = Path("samples/enhance_eval")
    out.mkdir(parents=True, exist_ok=True)
    for f in sys.argv[1:]:
        img = Image.open(f).convert("RGB")
        t = time.time()
        r = en.run(img)
        stem = Path(f).parent.name
        if r.get("candidate") is not None:
            r["candidate"].save(out / f"{stem}_candidate.png")
        if r.get("composite") is not None:
            r["composite"].save(out / f"{stem}_textsafe.png")
        v = r["validation"]
        v.pop("enhanced_lines", None)
        print(f"== {stem} {img.size}: accepted={r['accepted']} mode={r['mode']} {time.time() - t:.1f}s info={r['info']}")
        print("   by:", v.get("accepted_by"), "| reasons:", v.get("reasons"), "| full rejected:", v.get("full_enhancement_rejected"))
        print("   agreement", v.get("char_agreement"), "conf", v.get("confidence_restored"), "->", v.get("confidence_enhanced"),
              "lines", v.get("lines_restored"), "->", v.get("lines_enhanced"), "ink", v.get("ink_check"))
