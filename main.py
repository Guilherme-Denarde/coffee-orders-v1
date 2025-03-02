import functions_framework
import json
import uuid
import datetime
from flask import abort, Request
from google.cloud import firestore

# Initialize Firestore client
db = firestore.Client()
PEDIDOS_COLLECTION = "pedidos"
PRODUTOS_COLLECTION = "produtos"

def utc_now_iso():
    return datetime.datetime.utcnow().isoformat() + "Z"

@functions_framework.http
def api(request: Request):
    path = request.path
    method = request.method
    parts = path.split("/")

    # Orders routes
    is_pedidos_base = (len(parts) == 2 and parts[1] == "pedidos")
    is_pedidos_with_id = (len(parts) == 3 and parts[1] == "pedidos" and parts[2] != "")

    # Products routes
    is_produtos_base = (len(parts) == 2 and parts[1] == "produtos")
    is_produtos_with_id = (len(parts) == 3 and parts[1] == "produtos" and parts[2] != "")

    # Handle orders routes
    if is_pedidos_base:
        if method == "POST":
            return criar_pedido(request)
        elif method == "GET":
            return listar_pedidos(request)
        else:
            return abort(405, f"Method {method} not allowed on /pedidos")

    elif is_pedidos_with_id:
        pedido_id = parts[2]
        if method == "GET":
            return obter_pedido(request, pedido_id)
        elif method == "PATCH":
            return atualizar_status(request, pedido_id)
        elif method == "DELETE":
            return deletar_pedido(request, pedido_id)
        else:
            return abort(405, f"Method {method} not allowed on /pedidos/<id>")

    # Handle products routes
    elif is_produtos_base:
        if method == "POST":
            return criar_produto(request)
        elif method == "GET":
            return listar_produtos(request)
        else:
            return abort(405, f"Method {method} not allowed on /produtos")

    elif is_produtos_with_id:
        produto_id = parts[2]
        if method == "GET":
            return obter_produto(request, produto_id)
        elif method == "PUT":
            return atualizar_produto(request, produto_id)
        elif method == "DELETE":
            return deletar_produto(request, produto_id)
        else:
            return abort(405, f"Method {method} not allowed on /produtos/<id>")

    else:
        return abort(404, f"Path {path} not found")

# ------------------ PEDIDOS (Orders) ------------------ #

def criar_pedido(request: Request):
    """
    Cria um novo pedido e valida:
      - Se todos os produtos listados existem na base.
      - (Opcional) Se há estoque suficiente.
      - (Opcional) Substitui o preço do item pelo do banco (para consistência).
    """
    data = request.get_json(silent=True)
    if not data:
        return abort(400, "Invalid JSON body")

    if "cliente" not in data or "email" not in data or "itens" not in data:
        return abort(400, "Missing required fields: cliente, email, itens")

    novo_id = str(uuid.uuid4())
    agora = utc_now_iso()

    # Verify each product, get official price, and optionally check/update stock
    total = 0.0
    for item in data["itens"]:
        product_id = item.get("produto_id")
        if not product_id:
            return abort(400, "Cada item deve conter um 'produto_id'")
        if "quantidade" not in item:
            return abort(400, "Cada item deve conter uma 'quantidade'")

        produto_ref = db.collection(PRODUTOS_COLLECTION).document(product_id).get()
        if not produto_ref.exists:
            return abort(400, f"O produto com ID {product_id} não existe")

        produto_data = produto_ref.to_dict()

        # (Optional) Check stock
        qtd_solicitada = item["quantidade"]
        estoque_atual = produto_data.get("estoque", 0)
        if estoque_atual < qtd_solicitada:
            return abort(400, f"Estoque insuficiente para o produto '{produto_data.get('nome', product_id)}'")

        # Overwrite the item price from the DB for consistency
        preco_oficial = produto_data.get("preco", 0.0)
        item["preco"] = preco_oficial
        # Sums item line
        total += preco_oficial * qtd_solicitada

    novo_pedido = {
        "id": novo_id,
        "cliente": data["cliente"],
        "email": data["email"],
        "itens": data["itens"],
        "total": total,
        "status": "PENDENTE",
        "data_criacao": agora,
        "data_atualizacao": agora,
    }

    # Create the order
    db.collection(PEDIDOS_COLLECTION).document(novo_id).set(novo_pedido)

    # (Optional) Decrement the stock of each product
    # for item in data["itens"]:
    #     product_id = item["produto_id"]
    #     qtd_solicitada = item["quantidade"]
    #     produto_ref = db.collection(PRODUTOS_COLLECTION).document(product_id)
    #     produto_data = produto_ref.get().to_dict()
    #     produto_ref.update({
    #         "estoque": produto_data.get("estoque", 0) - qtd_solicitada,
    #         "data_atualizacao": utc_now_iso()
    #     })

    response_data = {
        "id": novo_id,
        "status": "PENDENTE",
        "total": total,
        "data_criacao": agora
    }
    return (json.dumps(response_data), 201, {"Content-Type": "application/json"})

def listar_pedidos(request: Request):
    pedidos_ref = db.collection(PEDIDOS_COLLECTION).stream()
    all_pedidos = []
    for p in pedidos_ref:
        pedido_data = p.to_dict()
        all_pedidos.append({
            "id": p.id,
            "cliente": pedido_data.get("cliente"),
            "email": pedido_data.get("email"),
            "total": pedido_data.get("total"),
            "status": pedido_data.get("status"),
            "itens": pedido_data.get("itens", []),
            "data_criacao": pedido_data.get("data_criacao", ""),
            "data_atualizacao": pedido_data.get("data_atualizacao", ""),
        })

    # Sort by data_criacao if available
    all_pedidos.sort(
        key=lambda x: x.get("data_criacao", ""),
        reverse=True
    )

    return (json.dumps(all_pedidos), 200, {"Content-Type": "application/json"})

def obter_pedido(request: Request, pedido_id_or_param: str):
    # Check if we're searching by client name (param: ?cliente=...)
    query_params = request.args
    search_by_client = query_params.get('cliente')

    if search_by_client:
        # Search by client name
        pedidos_ref = db.collection(PEDIDOS_COLLECTION).where("cliente", "==", search_by_client).limit(10).stream()
        results = []
        for doc in pedidos_ref:
            results.append(doc.to_dict())
        if not results:
            return abort(404, f"Nenhum pedido encontrado para o cliente: {search_by_client}")
        return (json.dumps(results), 200, {"Content-Type": "application/json"})
    else:
        # Search by ID
        pedido_ref = db.collection(PEDIDOS_COLLECTION).document(pedido_id_or_param).get()
        if not pedido_ref.exists:
            return abort(404, "Pedido não encontrado")
        return (json.dumps(pedido_ref.to_dict()), 200, {"Content-Type": "application/json"})

def atualizar_status(request: Request, pedido_id: str):
    pedido_ref = db.collection(PEDIDOS_COLLECTION).document(pedido_id)
    pedido = pedido_ref.get()

    if not pedido.exists:
        return abort(404, "Pedido não encontrado")

    data = request.get_json(silent=True)
    if not data or "status" not in data:
        return abort(400, "Missing 'status' in request body")

    allowed_status = ["PENDENTE", "PROCESSANDO", "ENVIADO", "CANCELADO"]
    if data["status"] not in allowed_status:
        return abort(400, f"Status inválido: {data['status']}")

    pedido_ref.update({
        "status": data["status"],
        "data_atualizacao": utc_now_iso()
    })

    response_data = {
        "message": "Pedido atualizado com sucesso",
        "status": data["status"]
    }
    return (json.dumps(response_data), 200, {"Content-Type": "application/json"})

def deletar_pedido(request: Request, pedido_id: str):
    pedido_ref = db.collection(PEDIDOS_COLLECTION).document(pedido_id)
    pedido = pedido_ref.get()
    if not pedido.exists:
        return abort(404, "Pedido não encontrado")

    pedido_ref.delete()
    return ("", 204)

# ------------------ PRODUTOS (Products) ------------------ #

def criar_produto(request: Request):
    data = request.get_json(silent=True)
    if not data:
        return abort(400, "Invalid JSON body")

    if "nome" not in data or "preco" not in data:
        return abort(400, "Missing required fields: nome, preco")

    novo_id = str(uuid.uuid4())
    agora = utc_now_iso()

    # imagens can be a list of URLs
    imagens = data.get("imagens")
    if imagens and not isinstance(imagens, list):
        return abort(400, "'imagens' deve ser uma lista de URLs ou omitido")

    novo_produto = {
        "id": novo_id,
        "nome": data["nome"],
        "preco": float(data["preco"]),
        "descricao": data.get("descricao", ""),
        "codigo": data.get("codigo", ""),
        "categoria": data.get("categoria", ""),
        "estoque": data.get("estoque", 0),
        "imagens": imagens if imagens else [],
        "data_criacao": agora,
        "data_atualizacao": agora,
    }

    db.collection(PRODUTOS_COLLECTION).document(novo_id).set(novo_produto)

    response_data = {
        "id": novo_id,
        "nome": data["nome"],
        "preco": float(data["preco"]),
        "data_criacao": agora
    }
    return (json.dumps(response_data), 201, {"Content-Type": "application/json"})

def listar_produtos(request: Request):
    # Check if we're filtering by category: ?categoria=...
    query_params = request.args
    filter_by_category = query_params.get('categoria')

    if filter_by_category:
        produtos_ref = db.collection(PRODUTOS_COLLECTION).where("categoria", "==", filter_by_category).stream()
    else:
        produtos_ref = db.collection(PRODUTOS_COLLECTION).stream()

    all_produtos = []
    for p in produtos_ref:
        produto_data = p.to_dict()
        all_produtos.append({
            "id": p.id,
            "nome": produto_data.get("nome"),
            "preco": produto_data.get("preco"),
            "descricao": produto_data.get("descricao", ""),
            "codigo": produto_data.get("codigo", ""),
            "categoria": produto_data.get("categoria", ""),
            "estoque": produto_data.get("estoque", 0),
            "imagens": produto_data.get("imagens", []),
            "data_criacao": produto_data.get("data_criacao", ""),
            "data_atualizacao": produto_data.get("data_atualizacao", ""),
        })

    # Sort by nome
    all_produtos.sort(key=lambda x: x.get("nome", ""))

    return (json.dumps(all_produtos), 200, {"Content-Type": "application/json"})

def obter_produto(request: Request, produto_id: str):
    # Check if we're searching by name: ?nome=...
    query_params = request.args
    search_by_name = query_params.get('nome')

    if search_by_name:
        produtos_ref = db.collection(PRODUTOS_COLLECTION).where("nome", "==", search_by_name).limit(10).stream()
        results = []
        for doc in produtos_ref:
            results.append(doc.to_dict())
        if not results:
            return abort(404, f"Nenhum produto encontrado com nome: {search_by_name}")
        return (json.dumps(results), 200, {"Content-Type": "application/json"})
    else:
        # Search by ID
        produto_ref = db.collection(PRODUTOS_COLLECTION).document(produto_id).get()
        if not produto_ref.exists:
            return abort(404, "Produto não encontrado")

        return (json.dumps(produto_ref.to_dict()), 200, {"Content-Type": "application/json"})

def atualizar_produto(request: Request, produto_id: str):
    produto_ref = db.collection(PRODUTOS_COLLECTION).document(produto_id)
    produto = produto_ref.get()

    if not produto.exists:
        return abort(404, "Produto não encontrado")

    data = request.get_json(silent=True)
    if not data:
        return abort(400, "Invalid JSON body")

    # Ensure price is a float if present
    if "preco" in data:
        try:
            data["preco"] = float(data["preco"])
        except ValueError:
            return abort(400, "Preço deve ser um número válido")

    # Ensure estoque is an integer if present
    if "estoque" in data:
        try:
            data["estoque"] = int(data["estoque"])
        except ValueError:
            return abort(400, "Estoque deve ser um número inteiro válido")

    # Ensure imagens is a list if present
    if "imagens" in data:
        if not isinstance(data["imagens"], list):
            return abort(400, "'imagens' deve ser uma lista de URLs")

    # Update with all provided fields + update timestamp
    update_data = {**data, "data_atualizacao": utc_now_iso()}
    produto_ref.update(update_data)

    response_data = {
        "message": "Produto atualizado com sucesso",
        "id": produto_id
    }
    return (json.dumps(response_data), 200, {"Content-Type": "application/json"})

def deletar_produto(request: Request, produto_id: str):
    produto_ref = db.collection(PRODUTOS_COLLECTION).document(produto_id)
    produto = produto_ref.get()

    if not produto.exists:
        return abort(404, "Produto não encontrado")

    # Check if product is referenced in any orders before deletion
    pedidos_ref = db.collection(PEDIDOS_COLLECTION).stream()
    for pedido in pedidos_ref:
        pedido_data = pedido.to_dict()
        for item in pedido_data.get("itens", []):
            if item.get("produto_id") == produto_id:
                return abort(400, f"Não é possível excluir o produto pois está vinculado ao pedido {pedido.id}")

    produto_ref.delete()
    return ("", 204)
