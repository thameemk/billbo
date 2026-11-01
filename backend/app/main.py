from importlib.metadata import version

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.expenses import router as expenses_router
from app.api.groups import router as groups_router
from app.api.tags import router as tags_router
from app.api.users import router as users_router
from app.core.config import get_settings

api_version = version("personal-expense-manager")
settings = get_settings()

app = FastAPI(
    title="Personal Expense Manager API",
    version=api_version,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)
app.include_router(users_router)
app.include_router(groups_router)
app.include_router(expenses_router)
app.include_router(tags_router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
