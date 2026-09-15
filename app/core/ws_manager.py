"""
Gerenciador de conexões WebSocket — uma "sala" por partida. Quando um ciclo
(regular, gatilho, ou sua sugestão) é criado/atualizado, todo mundo conectado
naquela partida recebe o evento na hora, sem precisar dar polling.
"""
import asyncio
import json
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.conexoes: dict[int, list[WebSocket]] = {}
        self.loop: asyncio.AbstractEventLoop | None = None

    def definir_loop(self, loop: asyncio.AbstractEventLoop):
        """Chamado uma vez, na inicialização da aplicação (ver main.py)."""
        self.loop = loop

    async def conectar(self, partida_id: int, ws: WebSocket):
        await ws.accept()
        self.conexoes.setdefault(partida_id, []).append(ws)

    def desconectar(self, partida_id: int, ws: WebSocket):
        if partida_id in self.conexoes and ws in self.conexoes[partida_id]:
            self.conexoes[partida_id].remove(ws)

    async def _broadcast_async(self, partida_id: int, mensagem: dict):
        mortos = []
        for ws in self.conexoes.get(partida_id, []):
            try:
                await ws.send_text(json.dumps(mensagem, default=str))
            except Exception:
                mortos.append(ws)
        for ws in mortos:
            self.desconectar(partida_id, ws)

    def broadcast(self, partida_id: int, mensagem: dict):
        """
        Chamado a partir de endpoints REST síncronos (rodando em thread separada
        do FastAPI) — usa run_coroutine_threadsafe pra entregar a mensagem sem
        bloquear a thread nem quebrar o loop de eventos principal.
        """
        if self.loop is None:
            return
        asyncio.run_coroutine_threadsafe(self._broadcast_async(partida_id, mensagem), self.loop)


manager = ConnectionManager()
