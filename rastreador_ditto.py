import os
import time
import random
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

# --- CONFIGURACIÓN ---
PRODUCTOS = [
    {
        "nombre": "Caja Ditto Premium",
        "url": "https://www.elcorteingles.es/juguetes/A202035453-30th-caja-coleccion-premium-ditto-de-celebracion-30-aniversario-de-jcc-pokemon-pokemon-bandai/",
    },
    {
        "nombre": "Caja Ditto Collection ING",
        "url": "https://www.elcorteingles.es/juguetes/A202035454-30th-ditto-collection-box-30th-celebration-pokemon-tcg-english-pokemon-bandai/",
    },
    {
        "nombre": "UPC 30 Aniversario",
        "url": "https://www.elcorteingles.es/juguetes/A202035441-30th-caja-coleccion-ultrapremium-de-celebracion-30-aniversario-de-jcc-pokemon-pokemon-bandai-modelos-surtidos/",
    },
    {
        "nombre": "Caja Mew Figura",
        "url": "https://www.elcorteingles.es/juguetes/A202035445-30th-caja-coleccion-con-figura-de-celebracion-30-aniversario-mew-de-jcc-pokemon-pokemon-bandai/",
    },
    {
        "nombre": "Caja Sylveon/Greninja EX",
        "url": "https://www.elcorteingles.es/juguetes/A202035447-30th-caja-coleccion-ex-celebracion-30-aniversario-de-jcc-pokemon-pokemon-bandai-modelos-surtidos/",
    },
    {
        "nombre": "Caja Mew/Mewtwo ING",
        "url": "https://www.elcorteingles.es/juguetes/A202042921-30th-figure-collection-30th-celebration-box-tcgenglish-pokemon-bandai-assorted-models/",
    },
    {
        "nombre": "Caja Poster 30 Aniversario",
        "url": "https://www.elcorteingles.es/juguetes/A202035450-30th-caja-coleccion-con-poster-de-celebracion-30-aniversario-de-jcc-pokemon-pokemon-bandai/",
    },
    {
        "nombre": "Blister Pegatinas",
        "url": "https://www.elcorteingles.es/juguetes/A202035442-30th-blister-coleccion-con-pegatinas-especiales-de-celebracion-30-aniversario-de-jcc-pokemon-pokemon-bandai-modelos-surtidos/",
    },
    {
        "nombre": "Mini Latas Surtido",
        "url": "https://www.elcorteingles.es/juguetes/A202035448-30th-minilata-celebracion-30-aniversario-de-jcc-pokemon-pokemon-bandai-modelos-surtidos/",
    },
    {
        "nombre": "Blister Sobres de Mejora",
        "url": "https://www.elcorteingles.es/juguetes/A202035444-30th-blister-de-sobres-de-mejora-de-celebracion-30-aniversario-de-jcc-pokemon-pokemon-bandai/",
    },
]

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")

# Duración máxima de cada ejecución (25 minutos = 1500s)
TIEMPO_MAXIMO_EJECUCION = 1500
ESPERA_ENTRE_RONDAS = 1


def enviar_alerta_discord(nombre_corto, titulo_web, precio, url):
    payload = {
        "username": "Alerta Stock ECI",
        "content": f"@everyone ¡HAY STOCK DE **{nombre_corto.upper()}**!",
        "embeds": [
            {
                "title": titulo_web,
                "url": url,
                "description": "¡El botón de compra está activo! Toca el título azul para entrar directo.",
                "color": 3066993,
                "fields": [
                    {"name": "Producto", "value": nombre_corto, "inline": True},
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
            print(f"[OK] Alerta enviada a Discord para {nombre_corto}.")
        else:
            print(f"[ERROR] Discord devolvió código {r.status_code}")
    except Exception as e:
        print(f"[ERROR] No se pudo conectar con Discord: {e}")


def comprobar_producto(page, producto):
    ahora = datetime.now().strftime("%H:%M:%S")
    nombre = producto["nombre"]
    url = producto["url"]

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=25000)
        page.wait_for_selector("h1", timeout=6000)
        page.wait_for_timeout(800)

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
            titulo_web = page.locator("h1").first.inner_text().strip() or nombre

            precio = "Ver en enlace"
            precio_el = page.locator("[class*='price'], [data-testid*='price']").first
            if precio_el.count() > 0:
                precio = precio_el.inner_text().strip().split("\n")[0]

            print(f"[{ahora}] ¡STOCK DETECTADO en {nombre}! Enviando a Discord...")
            enviar_alerta_discord(nombre, titulo_web, precio, url)
            return True
        else:
            print(f"[{ahora}] Sin stock: {nombre}")
            return False

    except Exception as e:
        print(f"[{ahora}] Error en {nombre}: {e}")
        return False


if __name__ == "__main__":
    if not DISCORD_WEBHOOK:
        print("ERROR: No se encontró el secret DISCORD_WEBHOOK.")
        exit(1)

    inicio = time.time()
    avisados_en_esta_sesion = set()
    print(f"Iniciando vigilancia rápida de {len(PRODUCTOS)} productos...")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            locale="es-ES",
            timezone_id="Europe/Madrid",
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        )

        # Bloquear imágenes, fuentes y vídeos para cargar cada ficha en < 1 segundo
        context.route(
            "**/*",
            lambda route: route.abort()
            if route.request.resource_type in ("image", "media", "font")
            else route.continue_(),
        )

        page = context.new_page()

        try:
            while (time.time() - inicio) < TIEMPO_MAXIMO_EJECUCION:
                for producto in PRODUCTOS:
                    if (time.time() - inicio) >= TIEMPO_MAXIMO_EJECUCION:
                        break

                    url = producto["url"]
                    if url not in avisados_en_esta_sesion:
                        encontrado = comprobar_producto(page, producto)
                        if encontrado:
                            avisados_en_esta_sesion.add(url)

                    # Pausa rápida entre productos (1.5 a 2.5 seg)
                    time.sleep(random.uniform(1.5, 2.5))

                if (time.time() - inicio + ESPERA_ENTRE_RONDAS) < TIEMPO_MAXIMO_EJECUCION:
                    time.sleep(ESPERA_ENTRE_RONDAS)
                else:
                    break
        finally:
            browser.close()

    print("Ronda finalizada correctamente.")
