import sys
from pathlib import Path
from fastapi import FastAPI

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

try:
    from main import app
except Exception as e:
    app = FastAPI()

    @app.get("/")
    def error_route():
        return {
            "status": "erro_na_importacao_do_main",
            "detalhe_do_erro": str(e)
        }
