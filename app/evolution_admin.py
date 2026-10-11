"""CLI de diagnóstico da Evolution, sem funções de envio."""

import argparse
import re
import sys

import httpx

from app.config import Settings

_INSTANCE_RE = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")


class EvolutionAdmin:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        instance: str,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not _INSTANCE_RE.fullmatch(instance):
            raise ValueError("EVOLUTION_INSTANCE deve conter apenas letras, números, _ ou -")
        if not api_key or not api_key.strip():
            raise ValueError("Defina EVOLUTION_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.instance = instance
        self.transport = transport

    def _request(self, method: str, path: str, *, read_timeout: float = 15.0, **kwargs) -> object:
        try:
            timeout = httpx.Timeout(15.0, connect=5.0, read=read_timeout)
            with httpx.Client(timeout=timeout, transport=self.transport) as client:
                response = client.request(
                    method,
                    self.base_url + path,
                    headers={"apikey": self.api_key},
                    **kwargs,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            # Não incluir o corpo: pode conter QR ou credenciais.
            raise RuntimeError(f"Evolution respondeu HTTP {exc.response.status_code}") from None
        except httpx.TimeoutException as exc:
            # Informar apenas a classe da falha: não expor URL, tokens nem QR.
            raise RuntimeError(f"Evolution excedeu o tempo limite ({type(exc).__name__})") from None
        except httpx.RequestError as exc:
            raise RuntimeError(f"Falha de conexão com Evolution ({type(exc).__name__})") from None
        except ValueError:
            raise RuntimeError("Evolution retornou JSON inválido") from None

    def create_instance(self) -> str:
        payload = self._request(
            "POST", "/instance/create",
            json={
                "instanceName": self.instance,
                "integration": "WHATSAPP-BAILEYS",
                "qrcode": False,
            },
        )
        if not isinstance(payload, dict) or not isinstance(payload.get("instance"), dict):
            raise RuntimeError("Resposta inesperada ao criar instância")
        return str(payload["instance"].get("instanceName", self.instance))

    def connection_state(self) -> str:
        payload = self._request("GET", f"/instance/connectionState/{self.instance}")
        if not isinstance(payload, dict) or not isinstance(payload.get("instance"), dict):
            raise RuntimeError("Resposta inesperada ao consultar conexão")
        state = payload["instance"].get("state")
        if not isinstance(state, str):
            raise RuntimeError("Estado da conexão ausente")
        return state

    def list_groups(self) -> list[tuple[str, str]]:
        payload = self._request(
            "GET", f"/group/fetchAllGroups/{self.instance}",
            params={"getParticipants": "false"},
            read_timeout=90.0,
        )
        if not isinstance(payload, list):
            raise RuntimeError("Resposta inesperada ao listar grupos")
        result = []
        for item in payload:
            if isinstance(item, dict):
                jid = item.get("id")
                if isinstance(jid, str) and jid.endswith("@g.us"):
                    subject = item.get("subject")
                    result.append((jid, subject if isinstance(subject, str) else "Sem nome"))
        return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Administração local da Evolution API")
    parser.add_argument("command", choices=["create", "status", "groups"])
    args = parser.parse_args(argv)
    settings = Settings.from_env()
    try:
        client = EvolutionAdmin(
            settings.evolution_base_url,
            settings.evolution_api_key,
            settings.evolution_instance,
        )
        if args.command == "create":
            print(f"Instância criada: {client.create_instance()}")
            print("Abra o Evolution Manager para obter o QR Code e parear.")
        elif args.command == "status":
            print(f"Estado da instância: {client.connection_state()}")
        else:
            groups = client.list_groups()
            print(f"Grupos encontrados: {len(groups)}")
            for jid, name in groups:
                print(f"{jid}  {name}")
    except (RuntimeError, ValueError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
