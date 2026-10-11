"""Fonte de catálogo substituível: busca local autorizada, nunca scraping."""

import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.discovery import CatalogItem, read_catalog


class CatalogUnavailable(Exception):
    pass


class InvalidCatalog(Exception):
    pass


def fold_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in text if not unicodedata.combining(char))


class CatalogProvider(Protocol):
    source: str

    def search(self, query: str, limit: int) -> list[CatalogItem]: ...


@dataclass(frozen=True)
class CsvCatalogProvider:
    path: Path
    source: str = "mercado_livre"

    def search(self, query: str, limit: int) -> list[CatalogItem]:
        try:
            items = read_catalog(self.path)
        except FileNotFoundError as exc:
            raise CatalogUnavailable(
                "Catálogo local não encontrado; carregue data/import/catalogo.csv"
            ) from exc
        except OSError as exc:
            raise CatalogUnavailable("Catálogo local indisponível") from exc
        except (ValueError, UnicodeError) as exc:
            raise InvalidCatalog("Catálogo CSV inválido") from exc
        terms = fold_text(query).split()
        return [
            item for item in items
            if all(term in fold_text(item.title) for term in terms)
        ][:limit]
