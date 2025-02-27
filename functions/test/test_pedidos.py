# tests/test_pedidos.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_listar_pedidos_401():
    """
    Testa se retorna 401 quando não enviamos token.
    """
    response = client.get("/pedidos")
    assert response.status_code == 401

# Exemplo de teste com token "falso" (seria preciso mockar ou usar um token real)
def test_listar_pedidos_com_token_invalido():
    response = client.get("/pedidos", headers={"Authorization": "Bearer ABC123"})
    assert response.status_code == 401
    
# pytest --maxfail=1 --disable-warnings -q
