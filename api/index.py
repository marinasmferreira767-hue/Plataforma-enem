from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "ok", "mensagem": "Servidor rodando perfeitamente na Vercel!"}
