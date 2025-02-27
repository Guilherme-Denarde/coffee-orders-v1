# routes/pedidos.py
from fastapi import APIRouter, HTTPException, Depends
from models import Pedido, PedidoStatus
from database import db
from datetime import datetime
from uuid import uuid4
from auth.firebase_auth import get_current_user  # verificação do token

router = APIRouter()


@router.post("/pedidos", status_code=201)
def criar_pedido(pedido: Pedido, user_info: dict = Depends(get_current_user)):
    """
    Cria um novo pedido no Firestore.
    Exemplo de body:
    {
      "cliente": "João Silva",
      "email": "joao@email",
      "itens": [
        {"produto": "Café Expresso", "quantidade": 2, "preco": 5.00}
      ]
    }
    """
    doc_id = str(uuid4())
    novo_pedido = {
        "id": doc_id,
        "cliente": pedido.cliente,
        "email": pedido.email,
        "itens": [item.dict() for item in pedido.itens],
        "total": sum(item.preco * item.quantidade for item in pedido.itens),
        "status": "PENDENTE",
        "data_criacao": datetime.utcnow().isoformat(),
        "data_atualizacao": datetime.utcnow().isoformat()
    }
    db.collection("pedidos").document(doc_id).set(novo_pedido)
    return novo_pedido


@router.get("/pedidos")
def listar_pedidos(user_info: dict = Depends(get_current_user)):
    """
    Retorna a lista de todos os pedidos.
    """
    pedidos = db.collection("pedidos").stream()
    return [p.to_dict() for p in pedidos]


@router.get("/pedidos/{id}")
def obter_pedido(id: str, user_info: dict = Depends(get_current_user)):
    """
    Retorna os detalhes de um pedido específico.
    """
    ref = db.collection("pedidos").document(id).get()
    if not ref.exists:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    return ref.to_dict()


@router.patch("/pedidos/{id}")
def atualizar_status(id: str, status: PedidoStatus, user_info: dict = Depends(get_current_user)):
    """
    Atualiza o status do pedido. Envie no body, por exemplo:
    { "status": "ENVIADO" }
    """
    ref = db.collection("pedidos").document(id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    ref.update({
        "status": status.value,
        "data_atualizacao": datetime.utcnow().isoformat()
    })
    return {"message": "Pedido atualizado com sucesso", "status": status.value}


@router.delete("/pedidos/{id}", status_code=204)
def deletar_pedido(id: str, user_info: dict = Depends(get_current_user)):
    """
    Remove um pedido. Retorna 204 No Content.
    """
    ref = db.collection("pedidos").document(id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    ref.delete()
    return  # 204 No Content
