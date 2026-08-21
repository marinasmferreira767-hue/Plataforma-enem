import sys
from pathlib import Path

# Adiciona o diretório raiz ao path para encontrar os arquivos do projeto
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from main import app
