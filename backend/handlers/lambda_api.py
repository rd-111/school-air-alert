"""Mangum adapter for running the FastAPI app in AWS Lambda."""

from mangum import Mangum

from app.main import app

handler = Mangum(app)
