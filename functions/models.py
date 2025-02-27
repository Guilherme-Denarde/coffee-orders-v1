# models.py
from pydantic import BaseModel
from typing import List
from enum import Enum

class Item(BaseModel):
    produto: str
    quantidade: int
    preco: float

class Pedido(BaseModel):
    cliente: str
    email: str
    itens: List[Item]

class PedidoStatus(str, Enum):
    PENDENTE = "PENDENTE"
    PROCESSANDO = "PROCESSANDO"
    ENVIADO = "ENVIADO"
    CANCELADO = "CANCELADO"
