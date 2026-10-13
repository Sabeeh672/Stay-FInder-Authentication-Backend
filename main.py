from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from database import setup_auth_database
from auth import router as auth_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_auth_database()
    yield

app = FastAPI(title="Authentication API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    if errors:
        msg = errors[0].get("msg", "Invalid input")
        return JSONResponse(status_code=400, content={"detail": msg.replace("Value error, ", "")})
    return JSONResponse(status_code=400, content={"detail": "Validation Error"})

app.include_router(auth_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)