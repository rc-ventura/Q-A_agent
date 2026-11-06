import difflib
import json
import sqlite3
import unicodedata

from langchain_core.tools import tool

from agent.tools.db import open_readonly

MAX_LIMIT = 10

_ROWS_SQL = """
SELECT p.product_id, p.name, p.description, p.specs, p.price_brl,
       p.stock_quantity, p.status, c.name AS category,
       v.discount_percent, v.final_price_brl, v.promotion_description AS campaign
FROM products p
JOIN categories c ON c.category_id = p.category_id
LEFT JOIN v_active_promotions v ON v.product_id = p.product_id
"""
_ACTIVE_ONLY = "WHERE p.status = 'active'"


def _norm(text: str | None) -> str:
    """Minusculas sem acentos para busca tolerante ("violao" acha "Violoes")."""
    return unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()


def _category_matches(wanted: str, category_name: str) -> bool:
    """Compara categoria pedida e real sem acento/caixa e tolerando singular/plural ("violao" casa "Violoes")."""
    name = _norm(category_name)
    return wanted in name or bool(difflib.get_close_matches(wanted, [name], cutoff=0.75))


def _final_price(row) -> float:
    """Preco efetivo: promocao ativa quando houver, senao preco de tabela."""
    return row["final_price_brl"] if row["final_price_brl"] is not None else row["price_brl"]


def _summary(row) -> dict:
    promo = None
    if row["discount_percent"] is not None:
        promo = {
            "discount_percent": row["discount_percent"],
            "final_price_brl": row["final_price_brl"],
            "campaign": row["campaign"],
        }
    return {
        "product_id": row["product_id"],
        "name": row["name"],
        "category": row["category"],
        "price_brl": row["price_brl"],
        "stock_quantity": row["stock_quantity"],
        "active_promotion": promo,
    }


def make_catalog_tools(db_path: str) -> list:
    """Cria os tools de catalogo fechados sobre o SQLite operacional.

    A conexao e read-only e aberta por chamada; base ausente degrada com
    {"error": "store_unavailable"} em vez de estourar no agente.
    """

    @tool
    def search_products(
        query: str = "",
        category: str = "",
        max_price_brl: float | None = None,
        in_stock_only: bool = True,
        limit: int = 5,
    ) -> str:
        """Busca instrumentos do catálogo por termo, categoria e teto de preço.

        Use para disponibilidade, preço, promoção ativa e comparações.
        A busca ignora acentos e caixa ("violao" acha "Violões") sobre
        nome, descrição e categoria. max_price_brl considera o preço
        FINAL (com promoção ativa). in_stock_only=True omite itens sem
        estoque; passe False para revelar indisponíveis e oferecer
        alternativas. category tolera acento e singular/plural ("violao"
        acha "Violões"); se o texto não for uma categoria existente (ex.:
        "sintetizador"), é usado como termo de busca. Ordena pelo menor preço final. Retorna JSON: lista
        de {product_id, name, category, price_brl, stock_quantity,
        active_promotion: {discount_percent, final_price_brl, campaign} | null},
        onde campaign é o nome da campanha ativa (ex.: "Oferta Especial").
        """
        try:
            conn = open_readonly(db_path)
        except sqlite3.Error:
            return json.dumps({"error": "store_unavailable"})
        try:
            rows = conn.execute(f"{_ROWS_SQL} {_ACTIVE_ONLY}").fetchall()
            category_names = [r[0] for r in conn.execute("SELECT name FROM categories")]
        finally:
            conn.close()
        tokens = [t for t in _norm(query).split() if t]
        cat = _norm(category)
        if cat and not any(_category_matches(cat, name) for name in category_names):
            tokens += cat.split()
            cat = ""
        matched_categories = set()
        for token in tokens:
            for cname in category_names:
                nc = _norm(cname)
                if token in nc or difflib.get_close_matches(token, [nc], cutoff=0.75):
                    matched_categories.add(nc)
        results = []
        for row in rows:
            if cat and not _category_matches(cat, row["category"]):
                continue
            if matched_categories and _norm(row["category"]) not in matched_categories:
                continue
            haystack = _norm(
                f"{row['name']} {row['description'] or ''} {row['category']}"
            )
            if tokens and not all(t in haystack for t in tokens):
                continue
            if max_price_brl is not None and _final_price(row) > max_price_brl:
                continue
            if in_stock_only and row["stock_quantity"] <= 0:
                continue
            results.append(_summary(row))
        results.sort(key=lambda i: i["active_promotion"]["final_price_brl"] if i["active_promotion"] else i["price_brl"])
        return json.dumps(results[: max(1, min(limit, MAX_LIMIT))], ensure_ascii=False)

    @tool
    def get_product_details(product_name: str) -> str:
        """Detalha um instrumento pelo nome: preço, estoque, specs e promoção.

        Use para aprofundar depois de search_products. Aceita nome parcial
        sem acentos ("takamine gd20"). Inclui produtos que não estão mais à
        venda: o campo status vale "active", "discontinued" (descontinuado,
        não faz mais parte do catálogo) ou "coming_soon" (em breve, ainda
        não disponível). Se não localizar, retorna
        {"error": "not_found", "did_you_mean": [nomes próximos]}.
        """
        try:
            conn = open_readonly(db_path)
        except sqlite3.Error:
            return json.dumps({"error": "store_unavailable"})
        try:
            rows = conn.execute(_ROWS_SQL).fetchall()
        finally:
            conn.close()
        tokens = [t for t in _norm(product_name).split() if t]
        # O modelo costuma antepor a categoria ao modelo ("ukulele Kalani KAL-700T"):
        # cada termo pode estar no nome ou na categoria do produto.
        matches = [
            row
            for row in rows
            if tokens
            and all(
                t in _norm(row["name"]) or _category_matches(t, row["category"]) for t in tokens
            )
        ]
        if not matches:
            suggestions = difflib.get_close_matches(
                _norm(product_name),
                [_norm(r["name"]) for r in rows],
                n=3,
                cutoff=0.4,
            )
            names = {
                _norm(r["name"]): r["name"] for r in rows
            }
            return json.dumps(
                {
                    "error": "not_found",
                    "did_you_mean": [names.get(s, s) for s in suggestions],
                },
                ensure_ascii=False,
            )
        best = max(matches, key=lambda r: difflib.SequenceMatcher(
            None, _norm(product_name), _norm(r["name"])
        ).ratio())
        details = _summary(best)
        details["status"] = best["status"]
        details["description"] = best["description"]
        try:
            details["specs"] = json.loads(best["specs"]) if best["specs"] else None
        except (json.JSONDecodeError, TypeError):
            details["specs"] = best["specs"]
        return json.dumps(details, ensure_ascii=False)

    return [search_products, get_product_details]
