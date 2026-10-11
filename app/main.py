import hmac
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.config import Settings
from app.domain import PublicationStatus, format_offer
from app.evolution import EvolutionPublisher
from app.storage import AlreadyPublishedOrInProgress, DuplicateOffer, SQLiteStore


class OfferCreate(BaseModel):
    source: str = Field(min_length=2, max_length=40)
    source_item_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=3, max_length=200)
    price_cents: int = Field(gt=0)
    reference_price_cents: int | None = Field(default=None, gt=0)
    affiliate_url: HttpUrl

    @field_validator("affiliate_url")
    @classmethod
    def require_https(cls, value: HttpUrl) -> HttpUrl:
        if value.scheme != "https":
            raise ValueError("Link de afiliado deve usar HTTPS")
        return value


def create_app(settings: Settings, publisher=None) -> FastAPI:
    store = SQLiteStore(settings.sqlite_path)
    publisher = publisher or EvolutionPublisher(
        settings.evolution_base_url, settings.evolution_api_key, settings.evolution_instance
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if not settings.admin_api_key:
            raise RuntimeError("Defina ADMIN_API_KEY antes de iniciar")
        store.initialize()
        yield

    app = FastAPI(title="Promo Radar", version="0.1.0", lifespan=lifespan)

    def admin(x_admin_key: str | None = Header(default=None)) -> None:
        if not x_admin_key or not hmac.compare_digest(x_admin_key, settings.admin_api_key):
            raise HTTPException(status_code=401, detail="Chave administrativa inválida")

    @app.get("/health")
    def health():
        if not store.health():
            raise HTTPException(status_code=503, detail="SQLite indisponível")
        return {"status": "ok", "schema_version": 2}

    @app.post("/api/v1/offers", status_code=201, dependencies=[Depends(admin)])
    def create_offer(payload: OfferCreate):
        try:
            return store.create_offer(
                {**payload.model_dump(exclude={"affiliate_url"}),
                 "affiliate_url": str(payload.affiliate_url)}
            )
        except DuplicateOffer:
            raise HTTPException(status_code=409, detail="Oferta já cadastrada") from None

    @app.get("/api/v1/offers", dependencies=[Depends(admin)])
    def list_offers(limit: int = 50):
        if limit < 1 or limit > 100:
            raise HTTPException(status_code=422, detail="limit deve estar entre 1 e 100")
        return store.list_offers(limit)

    @app.get("/api/v1/offers/{offer_id}", dependencies=[Depends(admin)])
    def get_offer(offer_id: str):
        offer = store.get_offer(offer_id)
        if not offer:
            raise HTTPException(status_code=404, detail="Oferta não encontrada")
        return offer

    @app.post("/api/v1/offers/{offer_id}/approve", dependencies=[Depends(admin)])
    def approve(offer_id: str):
        offer = store.approve(offer_id)
        if not offer:
            raise HTTPException(status_code=404, detail="Oferta não encontrada")
        return offer

    @app.get("/api/v1/offers/{offer_id}/preview", dependencies=[Depends(admin)])
    def preview(offer_id: str):
        offer = store.get_offer(offer_id)
        if not offer:
            raise HTTPException(status_code=404, detail="Oferta não encontrada")
        return {"message": format_offer(offer)}

    @app.post("/api/v1/offers/{offer_id}/publish", dependencies=[Depends(admin)])
    def publish(offer_id: str):
        if not settings.send_enabled:
            raise HTTPException(status_code=409, detail="Envio desabilitado: SEND_ENABLED=false")
        if not settings.whatsapp_group_id.endswith("@g.us"):
            raise HTTPException(status_code=409, detail="Configure WHATSAPP_GROUP_ID")
        offer = store.get_offer(offer_id)
        if not offer:
            raise HTTPException(status_code=404, detail="Oferta não encontrada")
        if offer["status"] != "APPROVED":
            raise HTTPException(status_code=409, detail="Oferta deve ser aprovada")
        try:
            record = store.claim_publication(offer_id, settings.whatsapp_group_id)
        except AlreadyPublishedOrInProgress:
            raise HTTPException(
                status_code=409, detail="Envio já existe; verifique a publicação antes de repetir"
            ) from None
        try:
            provider_id = publisher.send_text(settings.whatsapp_group_id, format_offer(offer))
        except Exception as exc:
            record = store.finish_publication(
                record["id"], PublicationStatus.UNKNOWN,
                error_summary=type(exc).__name__[:100],
            )
            raise HTTPException(
                status_code=502,
                detail={"publication_id": record["id"], "status": "UNKNOWN",
                        "message": "Resultado incerto; conferir no grupo antes de intervir"},
            ) from None
        return store.finish_publication(record["id"], PublicationStatus.SENT, provider_id)

    @app.get("/api/v1/publications/{publication_id}", dependencies=[Depends(admin)])
    def get_publication(publication_id: str):
        record = store.get_publication(publication_id)
        if not record:
            raise HTTPException(status_code=404, detail="Publicação não encontrada")
        return record

    return app


app = create_app(Settings.from_env())
