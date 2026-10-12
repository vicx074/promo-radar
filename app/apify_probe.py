"""Prova manual, cobrada, da busca via Apify. NÃO chamada automaticamente no CI."""
import argparse
import sys

from app.catalog import CatalogUnavailable, InvalidCatalog
from app.config import Settings
from app.live_catalog import ApifyCatalogProvider


def main():
    parser = argparse.ArgumentParser(description="Consulta real e paga na Apify, sem afiliados")
    parser.add_argument("query", help="Ex.: mouse gamer")
    parser.add_argument("--run-paid-probe", action="store_true",
                        help="Confirma executar requisição externa possivelmente cobrada")
    args = parser.parse_args()
    cfg = Settings.from_env()
    if not args.run_paid_probe:
        parser.error("A consulta pode gerar custo. Adicione --run-paid-probe para confirmar.")
    if not cfg.apify_token:
        parser.error("Configure APIFY_TOKEN no ambiente privado, sem colá-lo no terminal.")
    try:
        items = ApifyCatalogProvider(cfg.apify_token).search(args.query, 10)
    except (CatalogUnavailable, InvalidCatalog) as exc:
        print("Falha na coleta real: " + str(exc), file=sys.stderr)
        return 1
    print(f"Produtos recebidos: {len(items)}")
    for n, item in enumerate(items, 1):
        print(f"{n}. {item.title[:100]} — R$ {item.price_cents/100:.2f}")
        print("   " + item.product_url)
        print("   Imagem: " + ("sim" if item.image_url else "não"))
    if not items:
        print("Sem produtos: resultado vazio NÃO prova busca funcional.")
        return 2
    print("Confira manualmente os anúncios: preços e estoque não são garantidos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
