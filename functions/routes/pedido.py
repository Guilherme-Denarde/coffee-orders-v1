from fastapi import APIRouter, HTTPException
from models import Pedido
from database import db
from uuid import uuid4
from datetime import datetime

router = APIRouter()

@router.post("/pedidos")
def criar_pedido(pedido: Pedido):
    novo_pedido = {
        "id": str(uuid4()),
        "cliente": pedido.cliente,
        "email": pedido.email,
        "itens": [item.dict() for item in pedido.itens],
        "total": sum(item.preco * item.quantidade for item in pedido.itens),
        "status": "PENDENTE",
        "data_criacao": datetime.utcnow().isoformat(),
        "data_atualizacao": datetime.utcnow().isoformat()
    }
    db.collection("pedidos").document(novo_pedido["id"]).set(novo_pedido)
    return novo_pedido

@router.get("/pedidos")
def listar_pedidos():
    pedidos = db.collection("pedidos").stream()
    return [pedido.to_dict() for pedido in pedidos]

@router.get("/pedidos/{id}")
def obter_pedido(id: str):
    pedido_ref = db.collection("pedidos").document(id).get()
    if not pedido_ref.exists:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    return pedido_ref.to_dict()

@router.patch("/pedidos/{id}")
def atualizar_status(id: str, status: str):
    pedido_ref = db.collection("pedidos").document(id)
    if not pedido_ref.get().exists():
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    pedido_ref.update({"status": status, "data_atualizacao": datetime.utcnow().isoformat()})
    return {"message": "Pedido atualizado com sucesso", "status": status}

@router.delete("/pedidos/{id}")
def deletar_pedido(id: str):
    pedido_ref = db.collection("pedidos").document(id)
    if not pedido_ref.get().exists():
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    pedido_ref.delete()
    return {"message": "Pedido removido"}
