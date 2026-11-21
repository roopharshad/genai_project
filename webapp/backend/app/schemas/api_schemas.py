from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

# --- Auth ---
class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=6)
    confirm_password: Optional[str] = None
    full_name: str
    workspace_name: Optional[str] = "Personal Workspace"

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

# --- User ---
class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True

# --- Workspace ---
class WorkspaceCreate(BaseModel):
    name: str
    description: Optional[str] = None

class WorkspaceOut(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str]
    owner_id: str
    created_at: datetime
    member_count: Optional[int] = 1

    class Config:
        from_attributes = True

# --- Project ---
class ProjectCreate(BaseModel):
    workspace_id: str
    name: str
    description: Optional[str] = None

class ProjectOut(BaseModel):
    id: str
    workspace_id: str
    name: str
    description: Optional[str]
    created_at: datetime
    asset_count: Optional[int] = 0

    class Config:
        from_attributes = True

# --- Asset & Version ---
class AssetVersionOut(BaseModel):
    id: str
    asset_id: str
    version_number: int
    version_type: str
    stored_filename: str
    file_size: int
    width: int
    height: int
    model_id: Optional[str]
    config_summary: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True

class AssetOut(BaseModel):
    id: str
    project_id: str
    original_filename: str
    stored_filename: str
    file_size: int
    mime_type: str
    width: int
    height: int
    resolution_category: str
    status: str
    degradation_analysis: Optional[Dict[str, Any]]
    created_at: datetime
    versions: Optional[List[AssetVersionOut]] = []

    class Config:
        from_attributes = True

# --- Restoration ---
class JobCreateRequest(BaseModel):
    project_id: str
    asset_id: str
    model_id: str
    config_params: Optional[Dict[str, Any]] = None

class RestorationJobOut(BaseModel):
    id: str
    project_id: str
    asset_id: str
    model_id: str
    model_name: str
    status: str
    progress: int
    stage: str
    error_message: Optional[str]
    config_params: Optional[Dict[str, Any]]
    output_version_id: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

# --- Analytics & Evaluation ---
class EvaluationResultOut(BaseModel):
    id: str
    job_id: str
    asset_version_id: str
    has_reference: bool
    psnr: Optional[float]
    ssim: Optional[float]
    lpips: Optional[float]
    ocr_word_acc: Optional[float]
    ocr_char_acc: Optional[float]
    edge_preservation_score: Optional[float]
    inference_time_ms: Optional[float]
    model_memory_mb: Optional[float]
    metrics_detail: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True

class ExperimentOut(BaseModel):
    id: str
    experiment_code: str
    name: str
    description: Optional[str]
    model_id: str
    dataset_info: Optional[Dict[str, Any]]
    hyperparameters: Optional[Dict[str, Any]]
    metrics_summary: Optional[Dict[str, Any]]
    runtime_seconds: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True

# --- Notification ---
class NotificationOut(BaseModel):
    id: str
    title: str
    message: str
    notification_type: str
    is_read: bool
    link_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
