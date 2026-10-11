from decimal import Decimal
from enum import StrEnum


class OfferStatus(StrEnum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"


class PublicationStatus(StrEnum):
    SENDING = "SENDING"
    SENT = "SENT"  # Aceite HTTP, não entrega
    UNKNOWN = "UNKNOWN"


def format_brl(cents: int) -> str:
    amount = f"{Decimal(cents) / 100:,.2f}"
    return "R$ " + amount.replace(",", "_").replace(".", ",").replace("_", ".")


def discount_percent(price_cents: int, reference_price_cents: int | None) -> int | None:
    if reference_price_cents is None or reference_price_cents <= price_cents:
        return None
    return round((reference_price_cents - price_cents) * 100 / reference_price_cents)


def format_offer(offer: dict) -> str:
    lines = ["*OFERTA DE TECNOLOGIA*", "", offer["title"],
             f"Preço: *{format_brl(offer['price_cents'])}*"]
    discount = discount_percent(offer["price_cents"], offer["reference_price_cents"])
    if discount:
        lines.append(f"{discount}% abaixo do preço de referência informado")
    affiliate_url = offer.get("affiliate_url")
    product_url = offer.get("product_url")
    destination = affiliate_url or product_url
    lines += [f"Loja: {offer['source']}", f"Confira: {destination}"]
    if affiliate_url:
        lines += ["", "*Publicidade:* este link pode gerar comissão de afiliado."]
    else:
        lines += ["", "Link comum do produto; sem rastreamento de afiliado cadastrado."]
    lines.append("Preço e estoque sujeitos a alteração.")
    return "\n".join(lines)
