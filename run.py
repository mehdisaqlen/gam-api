# run.py
import os
import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))  # Render sets PORT env var
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",      # must be 0.0.0.0 for Render
        port=port,
        reload=False,        # no reload in production
    )
