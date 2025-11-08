# app/main.py
import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
from googleads import errors as googleads_errors
from .gam import build_client, grant_admin_for_email
from .gam import list_accessible_networks


app = FastAPI(title="GAM Access API", version="1.0.0")

class GrantRequest(BaseModel):
    email: EmailStr = Field(..., description="Email to grant Administrator access")
    networks: Optional[List[str]] = Field(
        default=None, description="List of network codes (defaults to GAM_NETWORKS env if omitted)"
    )

class GrantResult(BaseModel):
    network: str
    status: str
    userId: Optional[int] = None
    roleId: Optional[int] = None
    error: Optional[str] = None

class GrantResponse(BaseModel):
    email: EmailStr
    results: List[GrantResult]

def _env_networks() -> List[str]:
    raw = os.getenv("GAM_NETWORKS", "")
    return [n.strip() for n in raw.split(",") if n.strip()]

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.post("/grant-access", response_model=GrantResponse)
def grant_access(body: GrantRequest):
    networks = body.networks or _env_networks()
    if not networks:
        raise HTTPException(status_code=400, detail="No networks provided and GAM_NETWORKS env not set.")

    results: List[GrantResult] = []

    for code in networks:
        try:
            client = build_client(network_code=code)
            out = grant_admin_for_email(client, body.email)
            results.append(GrantResult(network=code, **out))
        except googleads_errors.GoogleAdsServerFault as e:
            results.append(GrantResult(network=code, status="error", error=str(e)))
        except Exception as e:
            results.append(GrantResult(network=code, status="error", error=str(e)))

    return GrantResponse(email=body.email, results=results)


@app.get("/networks")
def get_networks():
    try:
        return {"networks": list_accessible_networks()}
    except Exception as e:
        return {"error": str(e)}