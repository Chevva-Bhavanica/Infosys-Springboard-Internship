
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi
from pathlib import Path

from app_database import init_db
from routes.bugs import router as bugs_router

ROOT = Path(__file__).resolve().parent
UPLOAD_DIR = ROOT / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(
    title="Intelligent Bug Diagnosis Platform",
    description="M1.3 - Bug Submission Module API",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5174",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(bugs_router, prefix="/api")


@app.on_event("startup")
def startup():
    init_db()


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "module": "M1.3 Bug Submission"
    }


@app.get("/")
def root():
    return {
        "message": "Bug Diagnosis Platform API",
        "docs": "/docs"
    }


# Custom OpenAPI schema for Swagger file uploads
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Find the bug submission request schema
    for schema in openapi_schema.get(
        "components", {}
    ).get("schemas", {}).values():

        files_schema = schema.get(
            "properties", {}
        ).get("files")

        if files_schema:
            items_schema = files_schema.get("items", {})

            if items_schema.get("type") == "string":
                items_schema.pop("contentMediaType", None)
                items_schema["format"] = "binary"

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
