import threading
import time
from datetime import datetime, timezone
import numpy as np
from PIL import Image
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.entities import (
    RestorationJob,
    Asset,
    AssetVersion,
    EvaluationResult,
    Notification
)
from app.storage.file_storage import FileStorageService
from app.ml_engine.inference.registry import ModelRegistry
from app.ml_engine.evaluation.metrics import MetricCalculator
from app.ml_engine.evaluation.ocr_eval import OCREvaluator
from app.ml_engine.evaluation.edge_eval import EdgePreservationEvaluator

class TaskRunner:
    _inference_lock = threading.Lock()

    """
    Background Task Execution Engine.
    Executes asynchronous restoration jobs through defined stages:
    Queued -> Validating -> Processing -> Evaluating -> Completed.
    """

    @classmethod
    def execute_restoration_job(cls, job_id: str):
        """Thread worker target to execute job lifecycle."""
        db: Session = SessionLocal()
        try:
            job = db.query(RestorationJob).filter(RestorationJob.id == job_id).first()
            if not job:
                return

            job.status = "validating"
            job.progress = 15
            job.stage = "Validating input image and parameters"
            job.started_at = datetime.now(timezone.utc)
            db.commit()

            asset = db.query(Asset).filter(Asset.id == job.asset_id).first()
            if not asset:
                raise ValueError("Source asset record not found")

            # Load original image
            original_path = FileStorageService.get_file_path(asset.stored_filename)
            if not original_path or not original_path.exists():
                raise FileNotFoundError(f"Original image file missing from storage: {asset.stored_filename}")

            with Image.open(original_path) as pil_img:
                img_rgb = pil_img.convert("RGB")
                img_np = np.array(img_rgb)

            # Stage: Processing
            job.status = "processing"
            job.progress = 40
            job.stage = f"Executing {job.model_name} inference"
            db.commit()

            # Execute Model Inference
            config = job.config_params or {}
            def update_progress(value: int, label: str):
                job.progress = value
                job.stage = label
                db.commit()

            job.stage = "Waiting for document restoration processor"
            db.commit()
            with cls._inference_lock:
                job.progress = 40
                job.stage = f"Executing {job.model_name} inference"
                db.commit()
                restored_np, op_metrics = ModelRegistry.run_restoration(
                    model_id=job.model_id,
                    input_image_np=img_np,
                    config=config,
                    progress=update_progress
                )

            # Stage: Saving output
            job.progress = 75
            job.stage = "Saving restored asset version"
            db.commit()

            restored_pil = Image.fromarray(restored_np)
            stored_filename, file_size, width, height = FileStorageService.save_restored_image(restored_pil, format="PNG")

            # Determine next version number
            version_count = db.query(AssetVersion).filter(AssetVersion.asset_id == asset.id).count()
            new_version_num = version_count + 1

            new_version = AssetVersion(
                asset_id=asset.id,
                version_number=new_version_num,
                version_type="restored",
                stored_filename=stored_filename,
                file_size=file_size,
                width=width,
                height=height,
                model_id=job.model_id,
                config_summary={
                    "model_name": job.model_name,
                    "params": config,
                    "operational": op_metrics
                }
            )
            db.add(new_version)
            db.flush()

            # Stage: Evaluation
            job.status = "evaluating"
            job.progress = 90
            job.stage = "Computing UI structural and text evaluation metrics"
            db.commit()

            # Evaluation against reference (comparing restored against original or clean reference)
            psnr_val = MetricCalculator.calculate_psnr(restored_np, img_np)
            ssim_val = MetricCalculator.calculate_ssim(restored_np, img_np)
            lpips_val = MetricCalculator.calculate_lpips_approx(restored_np, img_np)
            edge_res = EdgePreservationEvaluator.evaluate(restored_np, img_np)
            ocr_res = OCREvaluator.evaluate_text_consistency(restored_np, img_np)

            # Document quality (before/after damage, ink preservation, OCR) against the cropped
            # page the restoration was made from, so sizes match.
            doc_quality = None
            try:
                from backend.services import quality_service
                stage_url = op_metrics.get("stages_url")
                ref = img_rgb
                if stage_url:
                    from app.ml_engine.inference.registry import STAGES_DIR
                    pre_png = STAGES_DIR / stage_url.rstrip("/").split("/")[-1] / "1_preprocessed.png"
                    if pre_png.exists():
                        ref = Image.open(pre_png).convert("RGB")
                rep = op_metrics.get("text_report") or {}
                doc_quality = quality_service.evaluate(ref, restored_pil, rep, None, rep.get("final_lines"))
                ref_np = np.array(ref.resize(restored_pil.size))
                psnr_val = MetricCalculator.calculate_psnr(restored_np, ref_np)
                ssim_val = MetricCalculator.calculate_ssim(restored_np, ref_np)
                lpips_val = MetricCalculator.calculate_lpips_approx(restored_np, ref_np)
                ocr_info = doc_quality.get("ocr") or {}
                if ocr_info.get("kind") == "agreement_with_original_reading":
                    ocr_res = {"estimated_character_accuracy": ocr_info.get("char_agreement"),
                               "estimated_word_accuracy": ocr_info.get("word_agreement"), "source": "PaddleOCR agreement"}
            except Exception as exc:  # quality is informational: never fail a finished restoration
                doc_quality = {"error": f"{type(exc).__name__}: {exc}"}

            eval_record = EvaluationResult(
                job_id=job.id,
                asset_version_id=new_version.id,
                has_reference=False,  # compared with the uploaded original, not a clean ground truth
                psnr=psnr_val,
                ssim=ssim_val,
                lpips=lpips_val,
                ocr_word_acc=ocr_res.get("estimated_word_accuracy") if ocr_res else None,
                ocr_char_acc=ocr_res.get("estimated_character_accuracy") if ocr_res else None,
                edge_preservation_score=edge_res.get("overall_edge_preservation_score") if edge_res else None,
                inference_time_ms=op_metrics.get("inference_time_ms"),
                model_memory_mb=op_metrics.get("memory_usage_mb"),
                metrics_detail={
                    "edge_evaluation": edge_res,
                    "ocr_evaluation": ocr_res,
                    "document_quality": doc_quality,
                    "operational": op_metrics
                }
            )
            db.add(eval_record)
            db.commit()

            # Final step: Enhancement. Runs only after restoration, validation and evaluation have
            # succeeded. The enhanced page is saved separately and kept only if PaddleOCR (or, for
            # unreadable handwriting, the ink-preservation check) confirms the text is unchanged.
            # A failure here never fails the job: the restored version stays the result.
            enhancement_note = cls._run_enhancement(db, job, asset, new_version, restored_pil, op_metrics, update_progress)

            # Complete Job
            job.output_version_id = new_version.id
            job.status = "completed"
            job.progress = 100
            job.stage = enhancement_note
            job.completed_at = datetime.now(timezone.utc)

            # Create notification
            notif = Notification(
                user_id=asset.project.created_by or "system",
                title="Restoration Completed",
                message=f"Restoration job for {asset.original_filename} completed using {job.model_name}.",
                notification_type="success",
                link_url=f"/projects/{asset.project_id}/comparison?assetId={asset.id}"
            )
            db.add(notif)

            db.commit()

        except Exception as e:
            db.rollback()
            job = db.query(RestorationJob).filter(RestorationJob.id == job_id).first()
            if job:
                job.status = "failed"
                job.stage = "Processing failed"
                job.error_message = str(e)
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
        finally:
            db.close()

    @classmethod
    def _run_enhancement(cls, db, job, asset, restored_version, restored_pil, op_metrics, update_progress) -> str:
        """Returns the job's final stage text. Provider details stay in the server log only."""
        import json
        from backend.services import enhancement_service
        from app.ml_engine.inference.registry import STAGES_DIR
        done = "Restoration, evaluation and enhancement completed successfully"
        if not enhancement_service.enabled():
            return "Restoration and evaluation completed successfully"
        update_progress(92, "Enhancement: starting")
        try:
            rep = op_metrics.get("text_report") or {}
            lines = rep.get("final_lines") if rep.get("ocr_reliable", True) and rep.get("final_lines") else None
            res = enhancement_service.run(restored_pil, lines, progress=update_progress)
            stage_url = op_metrics.get("stages_url")
            stage_dir = STAGES_DIR / stage_url.rstrip("/").split("/")[-1] if stage_url else None
            v = dict(res.get("validation") or {})
            v.pop("enhanced_lines", None)
            summary = {"accepted": res["accepted"], "mode": res["mode"], "validation": v,
                       "elapsed_s": (res.get("info") or {}).get("elapsed_s")}
            if stage_dir and stage_dir.is_dir():
                if res.get("candidate") is not None:
                    res["candidate"].save(stage_dir / "6_enhancement_candidate.png")
                if res["accepted"]:
                    res["image"].save(stage_dir / "6_enhanced.png")
                (stage_dir / "enhancement.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
            if not res["accepted"]:
                why = "; ".join(v.get("reasons") or []) or "validation failed"
                return f"Restoration and evaluation completed successfully; enhancement not applied ({why})"
            update_progress(99, "Enhancement: saving enhanced version")
            stored, size, w, h = FileStorageService.save_restored_image(res["image"], format="PNG")
            op = dict(op_metrics)
            op["steps"] = list(op_metrics.get("steps", [])) + [
                "Enhancement applied (" + ("full page" if res["mode"] == "full" else "background only, text pixels kept")
                + f"); verified by {v.get('accepted_by') or 'OCR agreement'}"]
            if stage_dir:
                op["stages"] = sorted(p.name for p in stage_dir.iterdir())
            n = db.query(AssetVersion).filter(AssetVersion.asset_id == asset.id).count()
            db.add(AssetVersion(asset_id=asset.id, version_number=n + 1, version_type="enhanced",
                                stored_filename=stored, file_size=size, width=w, height=h, model_id="enhancement",
                                config_summary={"model_name": "Enhancement", "source_version_id": restored_version.id,
                                                "enhancement": summary, "operational": op}))
            db.commit()
            return done
        except Exception as exc:  # noqa: BLE001
            import logging
            logging.getLogger("docrestore.enhancement").exception("enhancement step failed")
            db.rollback()
            return "Restoration and evaluation completed successfully; enhancement not applied (internal error)"

    @classmethod
    def dispatch_job(cls, job_id: str):
        """Asynchronously trigger job execution."""
        thread = threading.Thread(target=cls.execute_restoration_job, args=(job_id,), daemon=True)
        thread.start()
