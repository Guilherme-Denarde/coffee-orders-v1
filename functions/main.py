from fastapi import FastAPI
from routes.pedidos import router as pedidos_router
from mangum import Mangum
from firebase_admin import initialize_app

# Initialize Firebase
initialize_app()

# Create FastAPI app
app = FastAPI()

# Register API routes
app.include_router(pedidos_router)

# Adapt FastAPI to Firebase Functions
handler = Mangum(app)
