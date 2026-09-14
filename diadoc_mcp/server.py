#!/usr/bin/env python3
"""diadoc_mcp — MCP-сервер для Диадока (Контур, ЭДО).

Каталог собран из официальной документации developer.kontur.ru/doc/diadoc-api:
114 методов по документообороту, контрагентам, подписанию, МЧД, печатным
формам и событиям.

Авторизация у Диадока двухчастная: идентификатор приложения (выдаёт Контур) и
токен пользователя, оба едут в одном заголовке:
    Authorization: DiadocAuth ddauth_api_client_id=<id>,ddauth_token=<token>

Запуск:
    DIADOC_CLIENT_ID=... DIADOC_TOKEN=... python -m diadoc_mcp.server
"""
from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from schema_mcp_core.client import MarketplaceClient, ServiceConfig
from schema_mcp_core.entities import EntityIndex
from schema_mcp_core.registry import Catalog
from schema_mcp_core.tools import register_cabinet_tools, register_generic_tools
from schema_mcp_core.transport import run as run_transport

CATALOG_PATH = Path(__file__).with_name("endpoints.yaml")


def _build_headers(creds: dict[str, str]) -> dict[str, str]:
    # Порядок и запятая без пробела — как в документации Диадока; сервер
    # разбирает заголовок строкой, лишний пробел ломает авторизацию.
    client_id = creds.get("client_id", "")
    token = creds.get("token", "")
    return {"Authorization": f"DiadocAuth ddauth_api_client_id={client_id},ddauth_token={token}"}


DIADOC_CONFIG = ServiceConfig(
    name="diadoc",
    scheme="https",
    fields=["client_id", "token"],
    env_map={"client_id": "DIADOC_CLIENT_ID", "token": "DIADOC_TOKEN"},
    build_headers=_build_headers,
    allowed_host_suffixes=[".kontur.ru"],
    whoami=("diadoc_get_my_user", ["FullName", "Login"]),
)


# Адрес документации API уходит в описание инструментов со свободным путём:
# каталог коннекторов Claude требует, чтобы такой инструмент называл свой API.
# Присваиваем после конструктора: поле появилось в schema-mcp-core позже,
# и на уже опубликованном ядре вызов с этим аргументом свалил бы импорт.
DIADOC_CONFIG.api_docs = "https://developer.kontur.ru/doc/diadoc-api"

mcp = FastMCP("diadoc-mcp-ru")
# Сущности сервиса лежат рядом с каталогом: у ядра своего файла нет и быть
# не может, разделы у ЭДО и у вакансий разные.
entities = EntityIndex.load(Path(__file__).with_name("entities.yaml"))
catalog = Catalog.from_yaml(CATALOG_PATH, entities=entities)
client = MarketplaceClient(DIADOC_CONFIG)

register_generic_tools(
    mcp, svc="diadoc", client=client, catalog=catalog, entities=entities,
    key_help="Идентификатор приложения запрашивается у Контура (diadoc-api@skbkontur.ru), "
             "токен пользователя выдаёт метод Authenticate. Оба кладутся в "
             "DIADOC_CLIENT_ID и DIADOC_TOKEN.",
)
register_cabinet_tools(mcp, svc="diadoc", client=client, catalog=catalog)


def main() -> None:
    run_transport(mcp)


def cli() -> None:
    """Точка входа пакета: без аргументов сервер, с `doctor` диагностика."""
    import sys

    args = sys.argv[1:]
    if args and args[0] == "doctor":
        from schema_mcp_core.doctor import main as doctor_main

        raise SystemExit(doctor_main([("diadoc", "API Диадока (Контур)",
                                       "diadoc_mcp.server")], args[1:], "diadoc-mcp-ru"))
    if args:
        print(f"diadoc-mcp-ru: неизвестный аргумент {args[0]!r} (есть только 'doctor')",
              file=sys.stderr)
        raise SystemExit(2)
    main()


if __name__ == "__main__":
    main()
