import os
import time
import random
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

# --- CONFIGURACIÓN ---
URL_PRODUCTO = "https://www.elcorteingles.es/juguetes/A202035453-30th-caja-coleccion-premium-ditto-de-celebracion-30-aniversario-de-jcc-pokemon-pokemon-bandai/"
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")

# Duración máxima de cada ejecución (4 minutos y 15 segundos = 255s)
TIEMPO_MAXIMO_EJECUCION = 255
ESPERA_ENTRE_COMPROBACIONES = 40


def enviar_alerta_discord(titulo, precio):
    payload = {
        "username": "Alerta Stock ECI",
        "content": "@everyone ¡HAY STOCK DISPONIBLE!",
        "embeds": [
            {
                "title": titulo,
                "url": URL_PRODUCTO,
                "description": "¡El botón de compra está activo! Entra rápido antes de que se agote.",
                "color": 3066993,
                "fields": [
                    {"name": "Precio detectado", "value": precio, "inline": True},
                    {"name": "Tienda", "value": "El Corte Inglés", "inline": True},
                ],
                "footer": {
                    "text": f"Detectado a las {datetime.now().strftime('%H:%M:%S')} UTC"
                },
            }
        ],
    }
    try:
        r = requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)
        if r.status_code in (200, 204):
            print("[OK] Alerta enviada correctamente a Discord.")
        else:
            print(f"[ERROR] Discord devolvió código {r.status_code}")
    except Exception as e:
        print(f"[ERROR] No se pudo conectar con Discord: {e}")


def comprobar_stock(page):
    ahora = datetime.now().strftime("%H:%M:%S")
    try:
        page.goto(URL_PRODUCTO, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(4000)

        boton_comprar = page.locator(
            "button:has-text('Añadir a la cesta'), button:has-text('Comprar')"
        ).first

        hay_stock = False
        if boton_comprar.count() > 0 and boton_comprar.is_visible():
            esta_deshabilitado = boton_comprar.is_disabled()
            clases = boton_comprar.get_attribute("class") or ""
            if not esta_deshabilitado and "disabled" not in clases.lower():
                hay_stock = True

        if hay_stock:
            titulo = "Caja Colección Premium Ditto 30 Aniversario - JCC Pokémon"
            h1 = page.locator("h1").first
            if h1.count() > 0:
                titulo = h1.inner_text().strip()

            precio = "Ver en enlace"
            precio_el = page.locator("[class*='price'], [data-testid*='price']").first
            if precio_el.count() > 0:
                precio = precio_el.inner_text().strip().split("\n")[0]

            print(f"[{ahora}] ¡STOCK DETECTADO! Enviando mensaje a Discord...")
            enviar_alerta_discord(titulo, precio)
            return True
        else:
            print(f"[{ahora}] Sin stock todavía.")
            return False

    except Exception as e:
        print(f"[{ahora}] Error al cargar la ficha: {e}")
        return False


if __name__ == "__main__":
    if not DISCORD_WEBHOOK:
        print("ERROR: No se encontró el secret DISCORD_WEBHOOK.")
        exit(1)

    inicio = time.time()
    print("Iniciando ronda de vigilancia de 4 minutos...")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            locale="es-ES",
            timezone_id="Europe/Madrid",
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        )
        page = context.new_page()

        try:
            while (time.time() - inicio) < TIEMPO_MAXIMO_EJECUCION:
                encontrado = comprobar_stock(page)
                if encontrado:
                    break
                if (time.time() - inicio + ESPERA_ENTRE_COMPROBACIONES) < TIEMPO_MAXIMO_EJECUCION:
                    espera = ESPERA_ENTRE_COMPROBACIONES + random.randint(-5, 8)
                    time.sleep(espera)
                else:
                    break
        finally:
            browser.close()

    print("Ronda finalizada correctamente.")
