import os

import uvicorn

from bot.config import settings

if __name__ == "__main__":
    port = int(os.environ.get("PORT", settings.dashboard_port))
    uvicorn.run(
        "dashboard.app:app",
        host="0.0.0.0",
        port=port,
        reload=False,
    )
