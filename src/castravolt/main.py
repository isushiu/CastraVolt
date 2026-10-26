import logging
import time
from contextlib import asynccontextmanager
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

from castravolt.config import Settings
from castravolt.database import make_engine

logger = logging.getLogger('castravolt')


class SystemInfo(BaseModel):
    name: str = 'CastraVolt'
    version: str = '0.1.0'
    stage: Literal['foundation'] = 'foundation'
    capabilities: dict[str, bool] = {'accounts': False, 'projects': False, 'predictions': False}


class Liveness(BaseModel):
    status: Literal['alive'] = 'alive'


class Readiness(BaseModel):
    scope: Literal['foundation'] = 'foundation'
    status: Literal['ready', 'not_ready']
    database: Literal['connected', 'not_configured', 'unavailable']
    # Foundation health is not a promise that prediction serving is ready.
    predictions_available: bool = False


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.engine = make_engine(settings)
        yield
        if app.state.engine is not None:
            app.state.engine.dispose()

    app = FastAPI(title='CastraVolt API', version='0.1.0', lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                       allow_credentials=True, allow_methods=['GET', 'OPTIONS'],
                       allow_headers=['Content-Type', 'X-CSRF-Token'], expose_headers=['X-Request-ID'])

    @app.middleware('http')
    async def request_context(request: Request, call_next):
        request.state.request_id = str(uuid4())
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # Never return exception/connection text or configuration secrets.
            logger.error('unhandled_error request_id=%s', request.state.request_id)
            response = JSONResponse(status_code=500, content={
                'error': {'code': 'internal_error', 'message': 'The request could not be completed.',
                          'request_id': request.state.request_id}})
        response.headers['X-Request-ID'] = request.state.request_id
        logger.info('request method=%s status=%s duration_ms=%.1f request_id=%s',
                    request.method, response.status_code, (time.perf_counter()-start)*1000,
                    request.state.request_id)
        return response

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return JSONResponse(status_code=exc.status_code, content={'error': {
            'code': f'http_{exc.status_code}', 'message': str(exc.detail),
            'request_id': request.state.request_id}}, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={'error': {
            'code': 'invalid_request', 'message': 'Please check the request fields.',
            'request_id': request.state.request_id}})

    @app.get('/health/live', response_model=Liveness)
    def live():
        return Liveness()

    @app.get('/health/ready', response_model=Readiness,
             responses={503: {'model': Readiness}})
    def ready(request: Request):
        engine = request.app.state.engine
        database = 'not_configured'
        if engine is not None:
            try:
                with engine.connect() as connection:
                    connection.execute(text('SELECT 1'))
                database = 'connected'
            except SQLAlchemyError:
                database = 'unavailable'
        result = Readiness(status='ready' if database == 'connected' else 'not_ready', database=database)
        return JSONResponse(status_code=200 if database == 'connected' else 503,
                            content=result.model_dump())

    @app.get('/api/v1/system', response_model=SystemInfo)
    def system():
        return SystemInfo()

    return app


app = create_app()
