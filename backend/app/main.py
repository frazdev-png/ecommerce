"""
FastAPI Application Entry Point

Purpose: Main FastAPI application with middleware and configuration
Why it exists: Central entry point for the API application
Features: CORS, middleware, router registration, lifecycle events
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config.settings import settings
from app.database.mongodb import mongodb
from app.database.seed import seed_database
from app.utils.exceptions import AppException
from app.utils.response import error_response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    
    Handles startup and shutdown events for the FastAPI application.
    """
    # Startup
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"Debug mode: {settings.DEBUG}")
    
    # Connect to MongoDB
    await mongodb.connect_to_database()
    
    # Seed database with initial data (disabled temporarily due to bcrypt issue)
    # await seed_database()
    
    yield
    
    # Shutdown
    print("Shutting down application...")
    await mongodb.close_database_connection()
    print("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# ==================== CORS Middleware ====================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Exception Handlers ====================
@app.exception_handler(AppException)
async def app_exception_handler(request, exc: AppException):
    """
    Handle custom application exceptions
    
    Returns a standardized error response for custom exceptions.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(
            error=exc.message,
            details=exc.details
        )
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """
    Handle general exceptions
    
    Returns a standardized error response for unexpected errors.
    """
    if settings.DEBUG:
        # Return detailed error in debug mode
        return JSONResponse(
            status_code=500,
            content=error_response(
                error=str(exc),
                details={"type": type(exc).__name__}
            )
        )
    else:
        # Return generic error in production
        return JSONResponse(
            status_code=500,
            content=error_response(
                error="Internal server error"
            )
        )


# ==================== Root Endpoint ====================
@app.get("/")
async def root():
    """
    Root endpoint
    
    Returns basic information about the API.
    """
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "running",
        "docs": "/docs",
    }


# ==================== Health Check ====================
@app.get("/health")
async def health_check():
    """
    Health check endpoint
    
    Returns the health status of the application.
    """
    try:
        # Check database connection
        if mongodb.client:
            await mongodb.client.admin.command('ping')
            db_status = "connected"
        else:
            db_status = "disconnected"
    except Exception:
        db_status = "error"
    
    return {
        "status": "healthy",
        "database": db_status,
        "environment": settings.ENVIRONMENT,
    }


# ==================== Router Registration ====================
# Import and register routers here
from app.routers.health import router as health_router
from app.routers.auth import router as auth_router
from app.routers.products import router as products_router
from app.routers.categories import router as categories_router
from app.routers.cart import router as cart_router
from app.routers.orders import router as orders_router
from app.routers.admin import router as admin_router
from app.routers.ai import router as ai_router

app.include_router(health_router, prefix=settings.API_V1_PREFIX)
app.include_router(auth_router, prefix=settings.API_V1_PREFIX, tags=["auth"])
app.include_router(products_router, prefix=settings.API_V1_PREFIX, tags=["products"])
app.include_router(categories_router, prefix=settings.API_V1_PREFIX, tags=["categories"])
app.include_router(cart_router, prefix=settings.API_V1_PREFIX, tags=["cart"])
app.include_router(orders_router, prefix=settings.API_V1_PREFIX, tags=["orders"])
app.include_router(admin_router, prefix=settings.API_V1_PREFIX, tags=["admin"])
app.include_router(ai_router, prefix=settings.API_V1_PREFIX, tags=["ai"])


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else settings.WORKERS,
    )
