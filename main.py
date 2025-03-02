import functions_framework
from fastapi import FastAPI, HTTPException, status, Request
from pydantic import BaseModel, EmailStr
from typing import List, Dict
from uuid import uuid4
from datetime import datetime
from starlette.testclient import TestClient
from starlette.responses import JSONResponse


# ----------------------------------------------------
# 1. FastAPI Application Setup
# ----------------------------------------------------
app = FastAPI(title="Cadastro e Consulta de Pedidos (Serverless on GCF)")

class Item(BaseModel):
    produto: str
    quantidade: int
    preco: float

class PedidoCreate(BaseModel):
    cliente: str
    email: EmailStr
    itens: List[Item]

class Pedido(PedidoCreate):
    id: str
    total: float
    status: str   #  PENDENTE, PROCESSANDO, ENVIADO, CANCELADO
    data_criacao: datetime
    data_atualizacao: datetime

# In-memory store. Should replace this db for production.
pedidos_db: Dict[str, Pedido] = {}


# ----------------------------------------------------
# 2. FastAPI Routes
# ----------------------------------------------------
@app.post("/pedidos", status_code=status.HTTP_201_CREATED)
def criar_pedido(pedido: PedidoCreate):
    """
    Criar um novo pedido.
    
    - Calcula o total a partir dos itens.
    - Atribui um novo UUID ao pedido.
    - Salva no 'banco de dados' em memória.
    """
    novo_id = str(uuid4())
    agora = datetime.utcnow()
    total = sum(item.quantidade * item.preco for item in pedido.itens)

    novo_pedido = Pedido(
        id=novo_id,
        cliente=pedido.cliente,
        email=pedido.email,
        itens=pedido.itens,
        total=total,
        status="PENDENTE",
        data_criacao=agora,
        data_atualizacao=agora,
    )

    pedidos_db[novo_id] = novo_pedido
    return {
        "id": novo_id,
        "status": "PENDENTE",
        "total": total,
        "data_criacao": novo_pedido.data_criacao.isoformat() + "Z"
    }

@app.get("/pedidos")
def listar_pedidos():
    """
    Listar todos os pedidos com informações resumidas.
    """
    return [
        {
            "id": p.id,
            "cliente": p.cliente,
            "total": p.total,
            "status": p.status
        }
        for p in pedidos_db.values()
    ]

@app.get("/pedidos/{pedido_id}")
def obter_pedido(pedido_id: str):
    """
    Obter detalhes completos de um pedido específico.
    """
    pedido = pedidos_db.get(pedido_id)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    return {
        "id": pedido.id,
        "cliente": pedido.cliente,
        "email": pedido.email,
        "itens": pedido.itens,
        "total": pedido.total,
        "status": pedido.status,
        "data_criacao": pedido.data_criacao.isoformat() + "Z",
        "data_atualizacao": pedido.data_atualizacao.isoformat() + "Z",
    }

class StatusUpdate(BaseModel):
    status: str

@app.patch("/pedidos/{pedido_id}")
def atualizar_status(pedido_id: str, update: StatusUpdate):
    """
    Atualiza somente o status do pedido.
    """
    pedido = pedidos_db.get(pedido_id)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    allowed_status = ["PENDENTE", "PROCESSANDO", "ENVIADO", "CANCELADO"]
    if update.status not in allowed_status:
        raise HTTPException(status_code=400, detail="Status inválido")

    pedido.status = update.status
    pedido.data_atualizacao = datetime.utcnow()
    return {"message": "Pedido atualizado com sucesso", "status": pedido.status}

@app.delete("/pedidos/{pedido_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_pedido(pedido_id: str):
    """
    Deletar um pedido do sistema, retornando 204 No Content.
    """
    if pedido_id not in pedidos_db:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    del pedidos_db[pedido_id]
    return JSONResponse(content={}, status_code=status.HTTP_204_NO_CONTENT)


# ----------------------------------------------------
# 3. Google Cloud Function Adapter
# ----------------------------------------------------
# Create a TestClient to handle requests in the same process.
client = TestClient(app)

@functions_framework.http
def fastapi_function(request):
    """
    Google Cloud Functions entry point.
    Converts the incoming Flask-like `request` into a Starlette request
    which the FastAPI `TestClient` can process, then returns the response.
    """
    # 1. Extract the method and path
    method = request.method
    path = request.path

    # 2. Build query parameters string if present
    args_dict = request.args.to_dict()
    if args_dict:
        query_str = "?" + "&".join([f"{k}={v}" for k, v in args_dict.items()])
        path += query_str

    # 3. Convert headers to a dict
    headers = dict(request.headers)

    # 4. Extract body
    body = request.get_data()

    # 5. Forward the request to the FastAPI app
    response = client.request(method, path, headers=headers, data=body)

    # 6. Build the JSONResponse for GCF to return
    try:
        content = response.json()
    except Exception:
        content = response.text

    return JSONResponse(content=content, status_code=response.status_code)
