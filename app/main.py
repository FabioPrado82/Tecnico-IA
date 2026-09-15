from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import asyncio
import os

from app.routers import (
    atletas, partidas, confirmacao, scouting, auth,
    tempo_real, pos_jogo, chat, penaltis, voz, avaliacao, websocket,
    campeonatos, adversarios, clubes, patrocinadores, divulgacao,
)
from app.core.ws_manager import manager

app = FastAPI(
    title="Técnico com IA — Save FC",
    description="API do MVP: pré-jogo, tempo real e pós-jogo.",
    version="0.1.0",
)


@app.on_event("startup")
async def registrar_loop_websocket():
    manager.definir_loop(asyncio.get_running_loop())


os.makedirs("fotos_atletas", exist_ok=True)
app.mount("/fotos", StaticFiles(directory="fotos_atletas"), name="fotos")
app.mount("/app", StaticFiles(directory="static", html=True), name="static")

app.include_router(auth.router)
app.include_router(atletas.router)
app.include_router(partidas.router)
app.include_router(confirmacao.router)
app.include_router(scouting.router)
app.include_router(tempo_real.router)
app.include_router(pos_jogo.router)
app.include_router(chat.router)
app.include_router(penaltis.router)
app.include_router(voz.router)
app.include_router(avaliacao.router)
app.include_router(websocket.router)
app.include_router(campeonatos.router)
app.include_router(adversarios.router)
app.include_router(clubes.router)
app.include_router(patrocinadores.router)
app.include_router(divulgacao.router)


@app.get("/health")
def health():
    return {"status": "ok"}
