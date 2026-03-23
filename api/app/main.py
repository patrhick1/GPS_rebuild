from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.database import engine, Base
from app.routers import health, auth, assessments, dashboard, admin, master

# Create database tables
Base.metadata.create_all(bind=engine)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    debug=settings.DEBUG,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(auth.router)
app.include_router(assessments.router)
app.include_router(dashboard.router)
app.include_router(admin.router)
app.include_router(master.router)


@app.get("/")
async def root():
    return {
        "message": "Welcome to GPS Assessment Platform API",
        "version": settings.VERSION,
        "docs": "/docs"
    }
