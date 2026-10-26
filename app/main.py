from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI,Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import get_settings
from app.errors import ApiError
from app.middleware import RequestSizeLimit
from app.services.fpl import FplClient
from app.services.projections import ProjectionStore
from app.services.optimizer import OptimizerService
from app.routes import health,team,optimize,transfers

def create_app(settings=None,fpl_client=None):
    settings=settings or get_settings()
    fpl=fpl_client or FplClient(settings)
    @asynccontextmanager
    async def lifespan(application):
        yield
        fpl.close()
    application=FastAPI(title="FPL Cartel Personalized API",version="0.1.0",
        description="Precomputed projections + existing Python squad/optimizer rules. No model recalculation.",lifespan=lifespan)
    application.state.settings=settings
    application.state.projections=ProjectionStore(settings.projections_path)
    application.state.optimizer=OptimizerService(settings,application.state.projections,fpl)
    application.add_middleware(RequestSizeLimit,max_bytes=settings.max_request_bytes)
    application.add_middleware(CORSMiddleware,allow_origins=list(settings.allowed_origins),allow_credentials=False,
        allow_methods=["GET","POST","OPTIONS"],allow_headers=["Content-Type"],max_age=600)

    @application.exception_handler(ApiError)
    async def api_error(request:Request,error:ApiError):
        payload={"code":error.code,"message":error.message}
        if error.details is not None:payload["details"]=error.details
        headers={"Cache-Control":"no-store"}
        if error.code in {"optimizer_busy","fpl_rate_limited"}:headers["Retry-After"]="5"
        return JSONResponse(status_code=error.status,content={"error":payload},headers=headers)

    @application.exception_handler(RequestValidationError)
    async def invalid(request:Request,error:RequestValidationError):
        return JSONResponse(status_code=422,content={"error":{"code":"invalid_request","message":"Invalid request.",
            "details":[{"field":".".join(str(p) for p in e["loc"]),"reason":e["msg"]} for e in error.errors()]}})

    @application.exception_handler(Exception)
    async def unexpected(request:Request,error:Exception):
        logging.exception("Personalized API request failed",exc_info=error)
        headers={"Cache-Control":"no-store"}
        origin=request.headers.get("origin")
        if origin in settings.allowed_origins:headers.update({"Access-Control-Allow-Origin":origin,"Vary":"Origin"})
        return JSONResponse(status_code=500,content={"error":{"code":"optimizer_failed","message":"The optimizer could not complete the request."}},headers=headers)

    @application.middleware("http")
    async def no_store(request:Request,call_next):
        response=await call_next(request)
        response.headers["Cache-Control"]="no-store"
        return response

    for router in (health.router,team.router,optimize.router,transfers.router):application.include_router(router)
    return application

app=create_app()


