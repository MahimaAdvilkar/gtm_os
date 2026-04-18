from fastapi import FastAPI
from app.api.routes import accounts, campaigns, outcomes

app = FastAPI(
    title="GTM OS",
    description="Synthetic-buyer-calibrated GTM operating system",
    version="0.1.0",
)

app.include_router(accounts.router)
app.include_router(campaigns.router)
app.include_router(outcomes.router)


@app.get("/health")
def health():
    return {"status": "ok"}
