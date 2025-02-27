import logging
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from routes.pedidos import router as pedidos_router
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import initialize_app
from mangum import Mangum

logger = logging.getLogger("uvicorn")
logger.setLevel(logging.INFO)

# Create FastAPI app

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Change this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#  Middleware para logar requests temporariamente
class LogRequestMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.info(f"New request: {request.method} {request.url}")
        response = await call_next(request)
        logger.info(f"Response status: {response.status_code}")
        return response

app.add_middleware(LogRequestMiddleware)

app.include_router(pedidos_router)

handler = Mangum(app)
