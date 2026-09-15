from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import decodificar_access_token
from app.core.ws_manager import manager
from app.models.usuario import Usuario

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/partidas/{partida_id}")
async def ws_partida(websocket: WebSocket, partida_id: int, token: str = Query(...)):
    """
    Conexão em tempo real da tela do auxiliar. O token vem na query string
    (?token=...) porque o WebSocket nativo do navegador não permite mandar
    header Authorization customizado.
    """
    payload = decodificar_access_token(token)
    if payload is None:
        await websocket.close(code=4401)
        return

    db: Session = SessionLocal()
    usuario = db.get(Usuario, int(payload["sub"]))
    db.close()
    if usuario is None or not usuario.ativo:
        await websocket.close(code=4401)
        return

    await manager.conectar(partida_id, websocket)
    try:
        while True:
            # Não esperamos nada do cliente além de manter a conexão viva —
            # qualquer mensagem recebida é só descartada.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.desconectar(partida_id, websocket)
