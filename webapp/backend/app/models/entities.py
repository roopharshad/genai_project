import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Boolean, Integer, Float, ForeignKey, DateTime, JSON
)
from sqlalchemy.orm import relationship
from app.core.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default="standard_user", nullable=False) # owner, admin, member, standard_user, researcher, administrator
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=True, nullable=False)
    avatar_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False)

    # Relationships
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    owned_workspaces = relationship("Workspace", back_populates="owner", cascade="all, delete-orphan")
    workspace_memberships = relationship("WorkspaceMember", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    refresh_token = Column(String(500), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    is_revoked = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    user = relationship("User", back_populates="sessions")


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False)

    owner = relationship("User", back_populates="owned_workspaces")
    members = relationship("WorkspaceMember", back_populates="workspace", cascade="all, delete-orphan")
    invitations = relationship("Invitation", back_populates="workspace", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="workspace", cascade="all, delete-orphan")


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), default="member", nullable=False) # owner, admin, member, researcher
    joined_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    workspace = relationship("Workspace", back_populates="members")
    user = relationship("User", back_populates="workspace_memberships")


class Invitation(Base):
    __tablename__ = "invitations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    role = Column(String(50), default="member", nullable=False)
    token = Column(String(255), unique=True, index=True, nullable=False)
    status = Column(String(50), default="pending", nullable=False) # pending, accepted, expired, revoked
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    workspace = relationship("Workspace", back_populates="invitations")


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False)

    workspace = relationship("Workspace", back_populates="projects")
    assets = relationship("Asset", back_populates="project", cascade="all, delete-orphan")
    restoration_jobs = relationship("RestorationJob", back_populates="project", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="project", cascade="all, delete-orphan")


class Asset(Base):
    __tablename__ = "assets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    resolution_category = Column(String(50), default="standard") # low_res, standard, high_res
    status = Column(String(50), default="active") # active, archived, deleted
    degradation_analysis = Column(JSON, nullable=True) # blur score, noise estimation, jpeg compression estimate
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False)

    project = relationship("Project", back_populates="assets")
    versions = relationship("AssetVersion", back_populates="asset", cascade="all, delete-orphan")
    jobs = relationship("RestorationJob", back_populates="asset", cascade="all, delete-orphan")


class AssetVersion(Base):
    __tablename__ = "asset_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    asset_id = Column(String(36), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    version_type = Column(String(50), nullable=False) # original, restored
    stored_filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    model_id = Column(String(100), nullable=True)
    config_summary = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    asset = relationship("Asset", back_populates="versions")
    evaluations = relationship("EvaluationResult", back_populates="version", cascade="all, delete-orphan")


class RestorationJob(Base):
    __tablename__ = "restoration_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id = Column(String(36), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    model_id = Column(String(100), nullable=False)
    model_name = Column(String(255), nullable=False)
    status = Column(String(50), default="queued", nullable=False) # queued, validating, processing, evaluating, completed, failed, cancelled
    progress = Column(Integer, default=0, nullable=False) # 0 to 100 derived from measurable stages
    stage = Column(String(100), default="Queued in pipeline")
    error_message = Column(Text, nullable=True)
    config_params = Column(JSON, nullable=True)
    output_version_id = Column(String(36), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    project = relationship("Project", back_populates="restoration_jobs")
    asset = relationship("Asset", back_populates="jobs")
    evaluation = relationship("EvaluationResult", back_populates="job", uselist=False, cascade="all, delete-orphan")


class RestorationConfig(Base):
    __tablename__ = "restoration_configs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    model_id = Column(String(100), nullable=False)
    parameters = Column(JSON, nullable=False)
    is_default = Column(Boolean, default=False)
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)


class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    experiment_code = Column(String(50), unique=True, index=True, nullable=False) # E1 to E8
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    model_id = Column(String(100), nullable=False)
    dataset_info = Column(JSON, nullable=True)
    hyperparameters = Column(JSON, nullable=True)
    metrics_summary = Column(JSON, nullable=True)
    runtime_seconds = Column(Float, nullable=True)
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_id = Column(String(36), ForeignKey("restoration_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_version_id = Column(String(36), ForeignKey("asset_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    has_reference = Column(Boolean, default=True, nullable=False)
    psnr = Column(Float, nullable=True)
    ssim = Column(Float, nullable=True)
    lpips = Column(Float, nullable=True)
    ocr_word_acc = Column(Float, nullable=True)
    ocr_char_acc = Column(Float, nullable=True)
    edge_preservation_score = Column(Float, nullable=True)
    inference_time_ms = Column(Float, nullable=True)
    model_memory_mb = Column(Float, nullable=True)
    metrics_detail = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    job = relationship("RestorationJob", back_populates="evaluation")
    version = relationship("AssetVersion", back_populates="evaluations")


class Report(Base):
    __tablename__ = "reports"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    report_type = Column(String(50), default="quality_evaluation") # quality_evaluation, experiment_comparison, asset_summary
    stored_filename = Column(String(255), nullable=False)
    metrics_summary = Column(JSON, nullable=True)
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    project = relationship("Project", back_populates="reports")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(50), default="info") # info, success, warning, error
    is_read = Column(Boolean, default=False, nullable=False)
    link_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    user = relationship("User", back_populates="notifications")



class DocumentText(Base):
    """OCR text of an asset version, as read and as reviewed/corrected by a user."""
    __tablename__ = "document_texts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    asset_id = Column(String(36), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    version_id = Column(String(36), ForeignKey("asset_versions.id", ondelete="CASCADE"), nullable=True, index=True)
    ocr_lines = Column(JSON, nullable=True)          # [{text, score, box, unreadable}] as read by OCR
    edited_text = Column(Text, nullable=True)        # user-approved text (one line per OCR line)
    status = Column(String(30), default="draft")     # draft | approved
    updated_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False)
