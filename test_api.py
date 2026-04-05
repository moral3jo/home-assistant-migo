#!/usr/bin/env python3
"""
Script de prueba para la API de Saunier Duval MiGo (Netatmo Energy).

Uso:
    pip install aiohttp
    python test_api.py

Pide usuario y contraseña interactivamente y muestra el estado de la caldera.
"""
from __future__ import annotations

import asyncio
import getpass
import json
import sys
from datetime import datetime, timedelta

import aiohttp

BASE_URL = "https://app.netatmo.net"
CLIENT_ID = "na_client_android_sdbg"
CLIENT_SECRET = "28d36edf4ff395256555b2925688ffeb"
USER_PREFIX = "sdbg"
USER_AGENT = "MiGo/3.4.0 (Android)"


async def get_token(session: aiohttp.ClientSession, username: str, password: str) -> dict:
    print("\n[1/4] Autenticando...")
    data = {
        "grant_type": "password",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "username": username,
        "password": password,
        "user_prefix": USER_PREFIX,
        "scope": "read_thermostat write_thermostat",
    }
    async with session.post(
        f"{BASE_URL}/oauth2/token",
        data=data,
        headers={"User-Agent": USER_AGENT},
    ) as resp:
        body = await resp.json()
        if resp.status != 200:
            print(f"  ERROR HTTP {resp.status}: {body}")
            sys.exit(1)
        print(f"  OK — token obtenido, expira en {body.get('expires_in', '?')}s")
        return body


async def get_homes_data(session: aiohttp.ClientSession, token: str) -> dict:
    print("\n[2/4] Obteniendo homesdata (topología)...")
    async with session.get(
        f"{BASE_URL}/api/homesdata",
        headers={"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT},
    ) as resp:
        body = await resp.json()
        if resp.status != 200:
            print(f"  ERROR HTTP {resp.status}: {body}")
            sys.exit(1)
        homes = body.get("body", {}).get("homes", [])
        print(f"  OK — {len(homes)} casa(s) encontrada(s)")
        for h in homes:
            rooms = h.get("rooms", [])
            modules = h.get("modules", [])
            print(f"    • {h.get('name', '?')} (id={h['id']})  —  {len(rooms)} habitacion(es), {len(modules)} módulo(s)")
        print("\n  Payload completo (homesdata):")
        print(json.dumps(body.get("body", {}), indent=4, ensure_ascii=False))
        return body


async def get_home_status(session: aiohttp.ClientSession, token: str, home_id: str) -> dict:
    print(f"\n[3/4] Obteniendo homestatus para home_id={home_id}...")
    async with session.get(
        f"{BASE_URL}/api/homestatus",
        params={"home_id": home_id},
        headers={"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT},
    ) as resp:
        body = await resp.json()
        if resp.status != 200:
            print(f"  ERROR HTTP {resp.status}: {body}")
            sys.exit(1)
        return body


def print_status(status: dict) -> None:
    print("\n[4/4] Estado actual:")
    home = status.get("body", {}).get("home", {})

    rooms = home.get("rooms", [])
    if rooms:
        print("  Habitaciones:")
        for room in rooms:
            temp = room.get("therm_measured_temperature", "?")
            setpoint = room.get("therm_setpoint_temperature", "?")
            mode = room.get("therm_setpoint_mode", "?")
            print(f"    • {room.get('id', '?')}: {temp}°C actual / {setpoint}°C objetivo  [modo: {mode}]")

    modules = home.get("modules", [])
    if modules:
        print("  Módulos:")
        for mod in modules:
            boiler = mod.get("boiler_status")
            boiler_str = ""
            if boiler is not None:
                boiler_str = "  🔥 QUEMANDO" if boiler else "  ❄ parada"
            print(f"    • {mod.get('id', '?')} [{mod.get('type', '?')}]{boiler_str}")

    print("\n  Payload completo (body.home):")
    print(json.dumps(home, indent=4, ensure_ascii=False))


async def test_set_mode(session: aiohttp.ClientSession, token: str, home_id: str) -> None:
    print("\n[EXTRA] ¿Quieres probar cambiar de modo? (s/n): ", end="", flush=True)
    choice = input().strip().lower()
    if choice != "s":
        return

    print("  Elige modo:")
    print("    1) schedule  (estoy en casa)")
    print("    2) away      (modo ausente)")
    mode_choice = input("  Opción (1/2): ").strip()
    mode = "schedule" if mode_choice == "1" else "away"

    async with session.post(
        f"{BASE_URL}/api/setthermmode",
        json={"home_id": home_id, "mode": mode},
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": USER_AGENT,
        },
    ) as resp:
        body = await resp.json()
        if resp.status == 200:
            print(f"  OK — modo cambiado a '{mode}'")
        else:
            print(f"  ERROR HTTP {resp.status}: {body}")


async def main() -> None:
    print("=== Test API Saunier Duval MiGo ===")
    print("Usa las mismas credenciales que en la app MiGo.\n")

    username = input("Email: ").strip()
    password = getpass.getpass("Contraseña: ")

    async with aiohttp.ClientSession() as session:
        token_data = await get_token(session, username, password)
        access_token = token_data["access_token"]

        homes_data = await get_homes_data(session, access_token)
        homes = homes_data.get("body", {}).get("homes", [])

        if not homes:
            print("\nNo se encontraron casas en la cuenta.")
            return

        # Si hay varias casas, preguntar cuál usar
        if len(homes) == 1:
            home = homes[0]
        else:
            print("\nSelecciona una casa:")
            for i, h in enumerate(homes):
                print(f"  {i+1}) {h.get('name', '?')} ({h['id']})")
            idx = int(input("Número: ").strip()) - 1
            home = homes[idx]

        home_id = home["id"]

        status = await get_home_status(session, access_token, home_id)
        print_status(status)

        await test_set_mode(session, access_token, home_id)

    print("\nFin del test.")


if __name__ == "__main__":
    asyncio.run(main())
