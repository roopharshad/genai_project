from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    workspaces,
    projects,
    assets,
    restorations,
    comparisons,
    analytics,
    reports,
    settings,
    notifications,
    admin,
    document_ai
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["Workspaces"])
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_router.include_router(assets.router, prefix="/assets", tags=["Assets"])
api_router.include_router(restorations.router, prefix="/restorations", tags=["Restorations"])
api_router.include_router(comparisons.router, prefix="/comparisons", tags=["Comparisons"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(settings.router, prefix="/settings", tags=["Settings"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(admin.router, prefix="/admin", tags=["Administrator"])
api_router.include_router(document_ai.router, prefix="/document-ai", tags=["Document AI"])

