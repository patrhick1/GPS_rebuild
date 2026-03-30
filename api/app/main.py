from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.database import engine, Base
from app.core.rate_limits import limiter
from app.routers import health, auth, assessments, dashboard, admin, master, billing

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    debug=settings.DEBUG,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware setup
allowed_origins = settings.CORS_ORIGINS

# In production, validate that wildcards are not used with credentials
if not settings.DEBUG:
    if "*" in allowed_origins:
        raise ValueError(
            "Wildcard '*' not allowed in CORS_ORIGINS when allow_credentials=True in production. "
            "Please specify explicit origins in your environment configuration."
        )

# Log CORS configuration in debug mode
if settings.DEBUG:
    print(f"DEBUG: CORS allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=[],
    max_age=600,
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(auth.router)
app.include_router(assessments.router)
app.include_router(dashboard.router)
app.include_router(admin.router)
app.include_router(master.router)
app.include_router(billing.router)


@app.get("/")
async def root():
    return {
        "message": "Welcome to GPS Assessment Platform API",
        "version": settings.VERSION,
        "docs": "/docs"
    }
