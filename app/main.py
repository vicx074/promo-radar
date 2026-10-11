import hmac
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

from app.affiliate import AffiliateLinkError, validate_official_link
from app.auth import (OwnerAuth, cookie_name, verify_origin, verify_password)
from app.catalog import CatalogUnavailable, CsvCatalogProvider, InvalidCatalog
from app.config import Settings
from app.discovery import _valid_product_url
from app.domain import PublicationStatus, format_offer
from app.evolution import EvolutionPublisher
from app.media import MediaError, cache_image, download_image, load_image
from app.storage import (
    AffiliateLinkRequired,
    AffiliateOfferNotEditable,
    AlreadyPublishedOrInProgress,
    DuplicateOffer,
    SearchSelectionInvalid,
    SearchSnapshotExpired,
    SearchSnapshotNotFound,
    SQLiteStore,
)


class OwnerLogin(BaseModel):
    password: str = Field(min_length=1, max_length=1024)


class OfferCreate(BaseModel):
    source: str = Field(min_length=2, max_length=40)
    source_item_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=3, max_length=200)
    price_cents: int = Field(gt=0)
    reference_price_cents: int | None = Field(default=None, gt=0)
    affiliate_url: HttpUrl | None = None
    product_url: HttpUrl | None = None
    image_url: HttpUrl | None = None

    @field_validator("affiliate_url", "product_url", "image_url")
    @classmethod
    def require_https(cls, value: HttpUrl | None) -> HttpUrl | None:
        if value is not None and value.scheme != "https":
            raise ValueError("Link de afiliado deve usar HTTPS")
        return value

    @model_validator(mode="after")
    def require_product_or_link(self):
        if self.source == "mercado_livre":
            if not self.product_url:
                raise ValueError("Ofertas Mercado Livre exigem product_url")
            if not _valid_product_url(str(self.product_url)):
                raise ValueError("product_url deve ser uma URL de produto Mercado Livre")
            if self.affiliate_url is not None:
                raise ValueError("Cadastre link de afiliado no endpoint /affiliate-link")
        if self.source != "mercado_livre" and not self.affiliate_url:
            raise ValueError("Informe affiliate_url para esta fonte")
        return self


class AffiliateLinkRegister(BaseModel):
    affiliate_url: HttpUrl
    product_match_confirmed: bool

    @field_validator("affiliate_url")
    @classmethod
    def check_link_format(cls, value: HttpUrl) -> HttpUrl:
        try:
            validate_official_link(str(value))
        except AffiliateLinkError as exc:
            raise ValueError(str(exc)) from exc
        return value

    @model_validator(mode="after")
    def confirm_matching_product(self):
        if self.product_match_confirmed is not True:
            raise ValueError("Confirme que o link foi gerado para este produto")
        return self


class CatalogSearch(BaseModel):
    query: str = Field(min_length=2, max_length=100)
    limit: int = Field(default=20, ge=1, le=50)

    @field_validator("query")
    @classmethod
    def nonempty_query(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("Digite ao menos 2 caracteres no nicho")
        return normalized


class CatalogSelection(BaseModel):
    search_id: UUID
    source_item_ids: list[str] = Field(min_length=1, max_length=20)

    @field_validator("source_item_ids")
    @classmethod
    def unique_selection(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("Não repita o mesmo produto na seleção")
        if any(not item_id or len(item_id) > 64 for item_id in value):
            raise ValueError("IDs de produto inválidos")
        return value


def create_app(
    settings: Settings, publisher=None, image_loader=None, catalog_provider=None
) -> FastAPI:
    store = SQLiteStore(settings.sqlite_path)
    owner_auth = OwnerAuth(store)
    publisher = publisher or EvolutionPublisher(
        settings.evolution_base_url, settings.evolution_api_key, settings.evolution_instance
    )
    media_dir = settings.sqlite_path.parent / "media"
    if catalog_provider is None:
        catalog_provider = CsvCatalogProvider(
            settings.sqlite_path.parent / "import" / "catalogo.csv"
        )
    if image_loader is None:
        def image_loader(url):
            return download_image(url, settings.media_allowed_hosts)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if settings.allow_admin_api_key and not settings.admin_api_key:
            raise RuntimeError("Defina ADMIN_API_KEY antes de iniciar")
        if settings.single_owner_mode:
            if not settings.owner_password_hash.startswith("$argon2id$"):
                raise RuntimeError("Configure OWNER_PASSWORD_HASH Argon2id para acesso privado")
            if not settings.session_cookie_secure:
                raise RuntimeError("A VPS exige SESSION_COOKIE_SECURE=true")
            if settings.allow_admin_api_key:
                raise RuntimeError("Na VPS, configure ALLOW_ADMIN_API_KEY=false")
        store.initialize()
        yield

    app = FastAPI(title="Promo Radar", version="0.1.0", lifespan=lifespan)

    def session_only(request: Request) -> None:
        session = owner_auth.read_session(
            request.cookies.get(cookie_name(settings.session_cookie_secure))
        )
        if session is None:
            raise HTTPException(status_code=401, detail="Entre novamente no painel")
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            if not verify_origin(
                request.headers.get("origin"),
                request.headers.get("host"),
                secure=settings.session_cookie_secure,
            ):
                raise HTTPException(status_code=403, detail="Origem da solicitação inválida")
            submitted = request.headers.get("x-csrf-token", "")
            if not submitted or not hmac.compare_digest(submitted, session.csrf_token):
                raise HTTPException(status_code=403, detail="Proteção CSRF inválida")

    def admin(request: Request, x_admin_key: str | None = Header(default=None)) -> None:
        # A chave é compatibilidade para CLI/CI local; desativada em VPS privada.
        if (
            settings.allow_admin_api_key
            and x_admin_key
            and hmac.compare_digest(x_admin_key, settings.admin_api_key)
        ):
            return
        session_only(request)

    @app.post("/api/v1/auth/login")
    def login(payload: OwnerLogin, request: Request, response: Response):
        if not verify_origin(
            request.headers.get("origin"),
            request.headers.get("host"),
            secure=settings.session_cookie_secure,
        ):
            raise HTTPException(status_code=403, detail="Origem da solicitação inválida")
        if not settings.owner_password_hash:
            raise HTTPException(status_code=503, detail="Senha do painel não configurada")
        remaining = owner_auth.throttle_remaining()
        if remaining:
            raise HTTPException(
                status_code=429,
                detail="Muitas tentativas. Aguarde antes de tentar novamente.",
                headers={"Retry-After": str(remaining)},
            )
        if not verify_password(payload.password, settings.owner_password_hash):
            owner_auth.failed_login()
            raise HTTPException(status_code=401, detail="Senha incorreta")
        token, session = owner_auth.issue_session()
        response.set_cookie(
            key=cookie_name(settings.session_cookie_secure),
            value=token,
            path="/",
            secure=settings.session_cookie_secure,
            httponly=True,
            samesite="strict",
            max_age=12 * 60 * 60,
        )
        response.headers["Cache-Control"] = "no-store"
        return {"authenticated": True, "csrf_token": session.csrf_token,
                "expires_at": session.expires_at}

    @app.get("/api/v1/auth/session")
    def session(request: Request, response: Response):
        current = owner_auth.read_session(
            request.cookies.get(cookie_name(settings.session_cookie_secure))
        )
        if not current:
            raise HTTPException(status_code=401, detail="Sessão expirada")
        response.headers["Cache-Control"] = "no-store"
        return {"authenticated": True, "csrf_token": current.csrf_token,
                "expires_at": current.expires_at}

    @app.post("/api/v1/auth/logout", dependencies=[Depends(session_only)])
    def logout(request: Request, response: Response):
        owner_auth.revoke(
            request.cookies.get(cookie_name(settings.session_cookie_secure))
        )
        response.delete_cookie(
            key=cookie_name(settings.session_cookie_secure),
            path="/",
            secure=settings.session_cookie_secure,
            httponly=True,
            samesite="strict",
        )
        response.headers["Cache-Control"] = "no-store"
        return {"authenticated": False}

    @app.get("/health")
    def health():
        if not store.health():
            raise HTTPException(status_code=503, detail="SQLite indisponível")
        return {"status": "ok", "schema_version": 6}

    @app.post("/api/v1/discovery/search", dependencies=[Depends(admin)])
    def search_catalog(payload: CatalogSearch):
        try:
            found = catalog_provider.search(payload.query, payload.limit)
        except CatalogUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from None
        except InvalidCatalog as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        return store.save_search(payload.query, catalog_provider.source, found)

    @app.post("/api/v1/discovery/select", dependencies=[Depends(admin)])
    def select_catalog(payload: CatalogSelection):
        try:
            offers = store.select_search_items(
                str(payload.search_id), payload.source_item_ids
            )
        except SearchSnapshotNotFound:
            raise HTTPException(status_code=404, detail="Busca não encontrada") from None
        except SearchSnapshotExpired:
            raise HTTPException(
                status_code=410, detail="Busca expirada; pesquise novamente"
            ) from None
        except SearchSelectionInvalid:
            raise HTTPException(
                status_code=422, detail="Produto não encontrado nessa busca"
            ) from None
        return {"selected": offers}

    @app.get("/api/v1/affiliates/mercado-livre/status", dependencies=[Depends(admin)])
    def affiliate_status():
        return store.affiliate_connection_status()

    @app.post("/api/v1/offers", status_code=201, dependencies=[Depends(admin)])
    def create_offer(payload: OfferCreate):
        try:
            return store.create_offer(
                {**payload.model_dump(
                    exclude={"affiliate_url", "product_url", "image_url"}
                 ),
                 "product_url": str(payload.product_url) if payload.product_url else None,
                 "affiliate_url": (
                     str(payload.product_url)
                     if payload.source == "mercado_livre"
                     else str(payload.affiliate_url)
                 ),
                 "image_url": str(payload.image_url) if payload.image_url else None}
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

    @app.post(
        "/api/v1/offers/{offer_id}/affiliate-link", dependencies=[Depends(admin)]
    )
    def register_affiliate_link(offer_id: str, payload: AffiliateLinkRegister):
        try:
            result = store.register_affiliate_link(offer_id, str(payload.affiliate_url))
        except AffiliateOfferNotEditable:
            raise HTTPException(
                status_code=409,
                detail="Vínculo permitido somente em oferta Mercado Livre DRAFT",
            ) from None
        if not result:
            raise HTTPException(status_code=404, detail="Oferta não encontrada")
        return result

    @app.post("/api/v1/offers/{offer_id}/approve", dependencies=[Depends(admin)])
    def approve(offer_id: str):
        try:
            offer = store.approve(offer_id)
        except AffiliateLinkRequired:
            raise HTTPException(
                status_code=409, detail="Cadastre link de afiliado antes de aprovar"
            ) from None
        if not offer:
            raise HTTPException(status_code=404, detail="Oferta não encontrada")
        return offer

    @app.get("/api/v1/offers/{offer_id}/preview", dependencies=[Depends(admin)])
    def preview(offer_id: str):
        offer = store.get_offer(offer_id)
        if not offer:
            raise HTTPException(status_code=404, detail="Oferta não encontrada")
        media = store.media_for_offer(offer_id)
        return {
            "message": format_offer(offer),
            "image_url": offer["image_url"],
            "image_ready": media is not None,
            "image": (
                {"mime_type": media["mime_type"], "size_bytes": media["size_bytes"],
                 "width": media["width"], "height": media["height"]}
                if media else None
            ),
        }

    @app.post("/api/v1/offers/{offer_id}/prepare-media", dependencies=[Depends(admin)])
    def prepare_media(offer_id: str):
        offer = store.get_offer(offer_id)
        if not offer:
            raise HTTPException(status_code=404, detail="Oferta não encontrada")
        if offer["status"] != "DRAFT":
            raise HTTPException(status_code=409, detail="Preparar imagem antes da aprovação")
        if not offer["image_url"]:
            raise HTTPException(status_code=409, detail="Oferta não possui image_url")
        try:
            image = image_loader(offer["image_url"])
            name = cache_image(image, media_dir)
        except (MediaError, OSError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        result = store.attach_media(
            offer_id,
            {"sha256": image.sha256, "relative_path": name,
             "size_bytes": image.size_bytes, "width": image.width,
             "height": image.height},
        )
        if not result:
            raise HTTPException(status_code=409, detail="Oferta não está em DRAFT")
        return {
            "offer_id": offer_id, "image_ready": True, "size_bytes": image.size_bytes,
            "width": image.width, "height": image.height, "mime_type": "image/jpeg",
        }

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
        if offer["source"] == "mercado_livre" and not offer["affiliate_url"]:
            raise HTTPException(
                status_code=409, detail="Link oficial de afiliado não cadastrado"
            )
        media = store.media_for_offer(offer_id)
        if offer["image_url"] and not media:
            raise HTTPException(
                status_code=409, detail="Imagem precisa ser preparada antes de publicar"
            )
        if media:
            try:
                image_bytes = load_image(media_dir, media["sha256"])
            except (OSError, MediaError):
                raise HTTPException(
                    status_code=409, detail="Imagem armazenada indisponível ou inválida"
                ) from None
        try:
            record = store.claim_publication(offer_id, settings.whatsapp_group_id)
        except AlreadyPublishedOrInProgress:
            raise HTTPException(
                status_code=409, detail="Envio já existe; verifique a publicação antes de repetir"
            ) from None
        try:
            if media:
                provider_id = publisher.send_image(
                    settings.whatsapp_group_id, image_bytes, format_offer(offer)
                )
            else:
                provider_id = publisher.send_text(
                    settings.whatsapp_group_id, format_offer(offer)
                )
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
