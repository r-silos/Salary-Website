from fastapi import FastAPI

from app.api.compare import router as compare_router

app = FastAPI(
    title="Salary Fairness API",
    description="Compare a salary against BLS OEWS estimates with an optional H-1B LCA overlay.",
    version="0.1.0",
)
app.include_router(compare_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
