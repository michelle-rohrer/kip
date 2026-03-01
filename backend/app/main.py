from fastapi import FastAPI


app = FastAPI(
    title="kip API",
    description="Cycle-aware load monitoring backend.",
    version="0.1.0",
)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
