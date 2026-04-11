# Function Store REST API (Simplified Personal MVP)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.exceptions import LogicHiveError, ValidationError
from orchestrator import (
    do_get_async,
    do_save_async,
    do_search_async,
)

app = FastAPI(
    title="LogicHive API",
    description="Minimalist API for personal code asset management",
    version="1.0.0",
)

# CORS for local usage
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Models ---
class FunctionCreate(BaseModel):
    name: str  # Renamed for clarity
    code: str
    description: str | None = ""
    tags: list[str] | None = []
    language: str | None = "python"


class SearchQuery(BaseModel):
    query: str
    limit: int | None = 5


# --- Endpoints ---
@app.get("/")
def root():
    return {"message": "LogicHive API", "status": "running", "mode": "personal-mvp"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/functions")
async def create_function(func: FunctionCreate):
    """Save a new function (automatically optimized by AI)"""
    try:
        success = await do_save_async(
            name=func.name,
            code=func.code,
            description=func.description or "",
            tags=func.tags or [],
            language=func.language or "python",
        )
        return {"success": success, "name": func.name}
    except ValidationError as e:
        raise HTTPException(
            status_code=422,
            detail={"message": str(e), "details": getattr(e, "details", {})},
        )
    except LogicHiveError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/functions/{function_name}")
async def get_function(function_name: str):
    """Get a specific function by name."""
    try:
        result = await do_get_async(function_name)
        if not result:
            raise HTTPException(status_code=404, detail="Not found")
        return result
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/functions/search")
async def search(query: SearchQuery):
    """Semantic search for functions."""
    try:
        results = await do_search_async(query.query, query.limit or 5)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    print("Starting LogicHive REST API on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
