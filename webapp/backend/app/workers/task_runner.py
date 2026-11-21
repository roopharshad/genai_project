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
            restored_np, op_metrics = ModelRegistry.run_restoration(
                model_id=job.model_id,
                input_image_np=img_np,
                config=config
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

            eval_record = EvaluationResult(
                job_id=job.id,
                asset_version_id=new_version.id,
                has_reference=True,
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
                    "operational": op_metrics
                }
            )
            db.add(eval_record)

            # Complete Job
            job.output_version_id = new_version.id
            job.status = "completed"
            job.progress = 100
            job.stage = "Restoration and evaluation completed successfully"
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
    def dispatch_job(cls, job_id: str):
        """Asynchronously trigger job execution."""
        thread = threading.Thread(target=cls.execute_restoration_job, args=(job_id,), daemon=True)
        thread.start()
