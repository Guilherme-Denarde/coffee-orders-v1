from pydantic import BaseModel
from typing import List

class Item(BaseModel):
    produto: str
    quantidade: int
    preco: float

class Pedido(BaseModel):
    cliente: str
    email: str
    itens: List[Item]
