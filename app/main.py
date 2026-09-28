from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from fastapi.staticfiles import StaticFiles

from app.routers import auth, test_records, analytics, officers, records, export, media, kits, ai, admin, regions

app = FastAPI(
    title="NarcSeal API",
    description="Backend API for the NarcSeal Smart India Hackathon 2026 project.",
    version="1.0.0"
)

# Add CORS middleware for the dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the actual dashboard URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to NarcSeal Command Center API"}

# Mount the uploads directory to serve images
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# API v1 Router
api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(auth.router)
api_v1_router.include_router(test_records.router)
api_v1_router.include_router(analytics.router)
api_v1_router.include_router(officers.router)
api_v1_router.include_router(records.router)
api_v1_router.include_router(export.router)
api_v1_router.include_router(media.router)
api_v1_router.include_router(kits.router)
api_v1_router.include_router(ai.router)
api_v1_router.include_router(admin.router)
api_v1_router.include_router(regions.router)

# Include v1 router in the main app
app.include_router(api_v1_router)
