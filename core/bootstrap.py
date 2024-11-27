import importlib
import os
from typing import Annotated
from fastapi import Depends, FastAPI, Header, HTTPException
import uvicorn
from loguru import logger
from core.server_settings import server_settings
from dotenv import load_dotenv
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware


class Bootstrap:
    def __init__(self):
        load_dotenv()

        if server_settings.token == "":
            self.app = FastAPI(title=server_settings.app_name)
        else:
            self.app = FastAPI(title=server_settings.app_name, dependencies=[Depends(self.verify_token)])

    async def verify_token(self, x_token: Annotated[str, Header()]) -> None:
        if x_token != server_settings.token:
            raise HTTPException(status_code=400, detail="Token is invalid")

    def setup_middlewares(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["*"],
        )

    def setup_router(self):
        logger.info("Setting up routers")
        apps_dir = os.path.join(os.path.dirname(__file__), '..', 'apps')
        for app_name in os.listdir(apps_dir):
            app_path = os.path.join(apps_dir, app_name)
            if os.path.isdir(app_path):
                try:
                    module = importlib.import_module(f'apps.{app_name}.routes')
                    if hasattr(module, 'register_routes'):
                        module.register_routes(self.app)
                        logger.info(f"Registered routes for app: {app_name}")
                except ModuleNotFoundError:
                    logger.warning(f"Module not found for app: {app_name}")

    def start(self):
        self.setup_middlewares()
        self.setup_router()
        uvicorn.run(self.app, host=server_settings.app_host, port=server_settings.app_port)
