from app.domain import discount_percent, format_brl, format_offer


def test_brl_formats_integer_cents():
    assert format_brl(123456789) == "R$ 1.234.567,89"
    assert format_brl(15990) == "R$ 159,90"


def test_discount_not_claimed_when_reference_is_missing_or_lower():
    assert discount_percent(20000, None) is None
    assert discount_percent(20000, 15000) is None
    assert discount_percent(20000, 20000) is None
    assert discount_percent(15000, 20000) == 25


def test_message_identifies_advertising():
    message = format_offer({
        "title": "Teclado", "source": "Loja exemplo", "price_cents": 15000,
        "reference_price_cents": 20000, "affiliate_url": "https://example.org/ref",
    })
    assert "*Publicidade:*" in message
    assert "R$ 150,00" in message
    assert "25% OFF" in message
    assert "De: R$ 200,00" in message
    assert "Por: *R$ 150,00*" in message
