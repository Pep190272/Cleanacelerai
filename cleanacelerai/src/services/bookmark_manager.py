"""Service: browser bookmark extraction and management."""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class Bookmark:
    """A single browser bookmark."""
    id: str
    name: str
    url: str
    path: str
    category: str = ""
    subcategory: str = ""
    suggestion: str = ""
    original_name: str = ""


def detect_browsers() -> dict[str, str]:
    """
    Detect installed Chromium-based browsers and their bookmark file paths.

    Returns:
        Dict mapping display name → absolute path to Bookmarks file.
    """
    rutas: dict[str, str] = {}
    appdata = os.environ.get("LOCALAPPDATA", "")
    if not appdata:
        return rutas

    bases = {
        "Google Chrome": os.path.join(appdata, "Google", "Chrome", "User Data"),
        "Microsoft Edge": os.path.join(appdata, "Microsoft", "Edge", "User Data"),
        "Brave": os.path.join(appdata, "BraveSoftware", "Brave-Browser", "User Data"),
    }

    for nav_name, user_data_dir in bases.items():
        if not os.path.exists(user_data_dir):
            continue
        try:
            profiles_found: list[tuple[str, str]] = []
            for item in os.listdir(user_data_dir):
                perfil_dir = os.path.join(user_data_dir, item)
                if not os.path.isdir(perfil_dir):
                    continue
                bookmark_file = os.path.join(perfil_dir, "Bookmarks")
                if os.path.exists(bookmark_file):
                    # Only include browsers that actually have bookmarks
                    file_size = os.path.getsize(bookmark_file)
                    if file_size <= 100:
                        continue
                    try:
                        with open(bookmark_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        has_bookmarks = False
                        for raiz in data.get("roots", {}).values():
                            if isinstance(raiz, dict) and raiz.get("children"):
                                has_bookmarks = True
                                break
                        if not has_bookmarks:
                            continue
                    except (json.JSONDecodeError, OSError):
                        continue
                    profiles_found.append((item, bookmark_file))

            # Show profile name + email for identification
            for item, bookmark_file in profiles_found:
                profile_label = _get_profile_label(
                    os.path.join(user_data_dir, item),
                )
                if profile_label:
                    display_name = f"{nav_name} — {profile_label}"
                elif item == "Default":
                    display_name = nav_name
                else:
                    display_name = f"{nav_name} ({item})"
                rutas[display_name] = bookmark_file
        except OSError as exc:
            logger.debug("Could not scan browser profile directory %r: %s", user_data_dir, exc)

    return rutas


def _get_profile_label(profile_dir: str) -> str:
    """Extract a human-readable label from a Chrome/Edge profile (name + email)."""
    prefs_file = os.path.join(profile_dir, "Preferences")
    if not os.path.isfile(prefs_file):
        return ""
    try:
        with open(prefs_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        name = data.get("profile", {}).get("name", "").strip()
        accounts = data.get("account_info", [])
        email = accounts[0].get("email", "").strip() if accounts else ""
        if name and email:
            return f"{name} ({email})"
        if email:
            return email
        if name and name not in ("Persona 1", "Tu Chrome"):
            return name
        return ""
    except (json.JSONDecodeError, OSError, KeyError, IndexError):
        return ""


def _extract_nodes(nodo: Any, ruta: str = "") -> list[dict[str, str]]:
    """Recursively extract bookmark nodes from a Chrome/Edge JSON structure."""
    resultados: list[dict[str, str]] = []
    if not isinstance(nodo, dict):
        return resultados

    if nodo.get("type") == "url":
        resultados.append({
            "id": str(nodo.get("id", "")),
            "name": str(nodo.get("name", "")),
            "url": str(nodo.get("url", "")),
            "path": ruta,
        })
    elif nodo.get("type") == "folder" and "children" in nodo:
        nueva_ruta = f"{ruta} / {nodo.get('name', '')}" if ruta else str(nodo.get("name", ""))
        for hijo in nodo["children"]:
            resultados.extend(_extract_nodes(hijo, nueva_ruta))

    return resultados


def categorize_url(url: str) -> tuple[str, str]:
    """
    Categorize a URL by domain heuristics.

    Args:
        url: The bookmark URL.

    Returns:
        Tuple of (category_label, suggestion_text).
    """
    if not url:
        return "📁 Otros / Desconocido", "Evalúa si sirve, si no, bórralo."

    url_lower = url.lower()

    # ── SPECIFIC categories first (narrow matches) ──────────────────────

    rules: list[tuple[list[str], str, str]] = [
        # 1. IA — most specific, check first to avoid google catch-all
        (
            ["chatgpt", "openai", "anthropic", "huggingface", "gemini",
             "claude.ai", "midjourney", "zencoder",
             "perplexity", "copilot.microsoft", "poe.com", "bard", "ollama",
             "replicate.com", "runwayml", "elevenlabs", "suno.ai",
             "stability.ai", "together.ai", "groq.com", "deepl.com",
             "lmsys", "civitai"],
            "🤖 Inteligencia Artificial",
            "📂 Sugerencia: Mover a una carpeta 'Herramientas IA'. Son recursos de consulta rápida.",
        ),
        # 2. Aprendizaje — before Desarrollo to catch learning platforms
        (
            ["udemy", "coursera", "platzi", "freecodecamp", "w3schools",
             "mdn", "edx.", "codecademy", "khanacademy", "skillshare",
             "domestika", "masterclass", "egghead.io", "frontendmasters",
             "pluralsight", "lynda.com", "linkedin.com/learning",
             "tutorialspoint", "geeksforgeeks", "sololearn"],
            "📚 Aprendizaje y Cursos",
            "📂 Sugerencia: Agrupar en carpeta 'Cursos/Aprendizaje'. Separa por tema o plataforma.",
        ),
        # 3. Diseño — before Herramientas Online to catch design tools
        (
            ["figma", "canva", "dribbble", "behance", "adobe", "sketch.com",
             "pixlr", "pixabay", "pexels", "unsplash", "freepik", "flaticon",
             "iconfinder", "coolors", "colorhunt", "fontawesome",
             "stock.adobe", "crello", "vistacreate", "snappa",
             "iconmonstr", "icons8", "thenounproject", "invision"],
            "🎨 Diseño",
            "📂 Sugerencia: Agrupar en carpeta 'Diseño'. Herramientas visuales y de prototipado.",
        ),
        # 4. Herramientas Online — NEW category, specific tools
        (
            ["pinetools", "tinypng", "compressjpeg", "iloveimg", "remove.bg",
             "ezgif", "clideo", "online-video-cutter", "convertio",
             "smallpdf", "ilovepdf", "pdfescape", "pdf2go", "cloudconvert",
             "zamzar", "kapwing", "unscreen", "compressor.io", "squoosh",
             "imagecompressor"],
            "🔧 Herramientas Online",
            "📂 Sugerencia: Agrupar en carpeta 'Tools'. Herramientas web de uso puntual.",
        ),
        # 5. Desarrollo — specific dev domains
        (
            ["github.com", "stackoverflow", "developer.", "docs.microsoft", "npmjs",
             "aws.", "azure.", "vercel", "react",
             "gitlab", "bitbucket", "codepen", "jsfiddle", "repl.it",
             "gitbook", "readthedocs", "heroku", "netlify", "railway.app",
             "render.com", "fly.io", "digitalocean", "cloudflare",
             "cpanel", "plesk", "cdmon", "hostinger", "godaddy",
             "namecheap", "automatiza.dev", "dev.to", "hashnode",
             "angular.io", "vuejs.org", "svelte.dev", "nextjs.org",
             "nuxt.com", "deno.land", "bun.sh", "pypi.org",
             "packagist.org", "rubygems.org", "crates.io"],
            "💻 Desarrollo y Programación",
            "📂 Sugerencia: Agrupar en una carpeta 'Dev/Code'. Útiles para programar.",
        ),
        # 6. Entretenimiento
        (
            ["youtube", "netflix", "twitch", "spotify", "primevideo", "vimeo",
             "riverside.fm", "anchor.fm", "podcast", "deezer", "tidal",
             "soundcloud", "disneyplus", "hbomax", "crunchyroll",
             "dailymotion"],
            "🎬 Entretenimiento y Multimedia",
            "📂 Sugerencia: Crear carpeta 'Ocio'. Quitar de la vista principal para evitar distracciones.",
        ),
        # 7. Redes Sociales
        (
            ["facebook", "twitter", "x.com", "instagram", "linkedin",
             "reddit", "tiktok", "pinterest", "mastodon", "threads.net",
             "bluesky", "discord"],
            "📱 Redes Sociales",
            "📂 Sugerencia: Agrupar en 'Social'. Evita tenerlos sueltos en la barra principal.",
        ),
        # 8. Compras
        (
            ["amazon", "ebay", "aliexpress", "mercadolibre", "pccomponentes",
             "walmart", "bestbuy", "newegg", "etsy", "shein", "temu"],
            "🛒 Compras y Tiendas",
            "📂 Sugerencia: Mover a carpeta 'Compras/Shopping' para no mezclar con trabajo.",
        ),
        # 9. Noticias
        (
            ["wikipedia", "medium", "news.", "elpais", "bbc", "marca", "elmundo",
             "cnn", "reuters", "substack"],
            "📰 Noticias e Información",
            "📂 Sugerencia: Agrupar en 'Prensa/Lectura'. Leer fuera del horario productivo.",
        ),
        # 10. Finanzas
        (
            ["paypal", "binance", "tradingview", "banco", "coinmarketcap",
             "revolut", "wise.com", "stripe.com", "coinbase"],
            "🏦 Finanzas y Bancos",
            "🔒 Sugerencia: Crear carpeta segura 'Finanzas/Bancos'. No mezclar con ocio.",
        ),
    ]

    for domains, categoria, sugerencia in rules:
        if any(d in url_lower for d in domains):
            return categoria, sugerencia

    # ── BROAD catch-all rules (after specific ones) ────────────────────

    # Productividad — broad patterns including Google catch-all
    productividad_domains = [
        "mail.google", "docs.google", "notion", "trello", "slack",
        "office.com", "drive.google", "meet.", "calendar.", "translate.",
        "bitly", "app.bitly", "zapier", "ifttt", "airtable", "asana",
        "monday.com", "clickup", "basecamp", "evernote", "todoist",
        "webmail", "inbox.", "outlook.",
        "bing.com", "search.", "sites.google",
        "support.google", "chrome.google",
    ]
    if any(d in url_lower for d in productividad_domains):
        return (
            "💼 Productividad y Trabajo",
            "⭐ Sugerencia: MANTENER en la 'Barra de marcadores' principal si se usan a diario.",
        )

    # Google catch-all — any remaining google.com/google.es → Productividad
    if "google.com" in url_lower or "google.es" in url_lower:
        return (
            "💼 Productividad y Trabajo",
            "⭐ Sugerencia: MANTENER en la 'Barra de marcadores' principal si se usan a diario.",
        )

    return "🌐 Sitios Web Generales", "📂 Sugerencia: Clasificar manualmente en una carpeta 'Varios' o eliminar si ya no lo usas."


def categorize_by_content(name: str, url: str) -> tuple[str, str] | None:
    """Categorize a bookmark by analyzing its title and URL path keywords.

    This is the SECOND pass — called only when domain-based categorize_url()
    returns 'Sitios Web Generales'. Analyzes the text content of the bookmark
    name and URL path to find keyword matches.

    Returns:
        (category, suggestion) tuple, or None if no match found.
    """
    text = f"{name} {url}".lower()

    # Order matters: most specific first
    _content_rules: list[tuple[list[str], str, str]] = [
        # SEO & Marketing
        (
            ["seo", "keyword", "backlink", "serp", "ranking", "indexación",
             "posicionamiento", "link building", "anchor text", "domain authority",
             "page authority", "crawl", "sitemap", "robots.txt", "search console",
             "analytics", "tag manager", "remarketing", "retargeting",
             "sem", "adwords", "ads manager", "conversion", "funnel",
             "landing page", "lead", "crm", "email marketing", "newsletter",
             "mailchimp", "sendinblue", "brevo", "mailing"],
            "💻 Desarrollo y Programación",
            "📂 Sugerencia: Agrupar en 'SEO/Marketing'. Herramientas de posicionamiento.",
        ),
        # Blogging & Content
        (
            ["blog", "blogger", "bloggers", "wordpress", "wp-admin",
             "income report", "monetiz", "adsense", "affiliate",
             "content creator", "copywriting", "redacción"],
            "💻 Desarrollo y Programación",
            "📂 Sugerencia: Agrupar en 'Blogging/Content'. Recursos para crear contenido.",
        ),
        # Video/Image editing tools
        (
            ["video editor", "editor de video", "video maker", "recortar video",
             "cortar video", "convertir video", "video converter",
             "screen record", "grabador de pantalla", "downloader",
             "descargar video", "subtitle", "subtítulo"],
            "🔧 Herramientas Online",
            "📂 Sugerencia: Agrupar en 'Herramientas/Video'.",
        ),
        (
            ["image editor", "editor de imagen", "comprimir imagen",
             "compress image", "resize image", "redimensionar",
             "recortar imagen", "crop image", "collage",
             "background remov", "quitar fondo", "marca de agua",
             "watermark", "screenshot", "captura de pantalla"],
            "🔧 Herramientas Online",
            "📂 Sugerencia: Agrupar en 'Herramientas/Imagenes'.",
        ),
        # Design & Visual
        (
            ["diseño", "design", "plantilla", "template", "mockup",
             "wireframe", "prototip", "logo", "tipograf", "typography",
             "paleta", "palette", "color scheme", "ilustra", "vector",
             "svg", "icon", "stock photo", "foto de stock", "imagen gratis",
             "free image", "banco de imágenes", "font", "fuente",
             "texture", "textura", "photopea", "photoshop",
             "photo edit", "imagen", "imágenes", "imatges",
             "sonido", "sound effect", "stock video", "footage",
             "overlay", "brush", "gradient", "banner"],
            "🎨 Diseño",
            "📂 Sugerencia: Agrupar en 'Diseño'. Recursos visuales.",
        ),
        # AI & Machine Learning
        (
            ["inteligencia artificial", "artificial intelligence",
             "machine learning", "deep learning", "neural network",
             "red neuronal", "modelo de lenguaje", "language model",
             "prompt", "text to image", "text to video",
             "generative", "generativa", "llm", "gpt", "diffusion",
             "transformer", "fine-tun", "train model"],
            "🤖 Inteligencia Artificial",
            "📂 Sugerencia: Mover a 'IA'. Recursos de inteligencia artificial.",
        ),
        # Hosting & Web infrastructure
        (
            ["hosting", "alojamiento", "dominio", "domain", "dns",
             "ssl", "certificado", "cpanel", "whois", "servidor",
             "server", "vps", "cloud", "deploy", "ci/cd", "pipeline"],
            "💻 Desarrollo y Programación",
            "📂 Sugerencia: Agrupar en 'Hosting/Infra'. Infraestructura web.",
        ),
        # Web development tools
        (
            ["html", "css", "javascript", "python", "php", "java ",
             "typescript", "node.js", "api", "framework", "library",
             "código", "code", "programación", "programming",
             "developer", "desarrollo web", "web development",
             "debug", "devtools", "inspector", "console"],
            "💻 Desarrollo y Programación",
            "📂 Sugerencia: Agrupar en 'Dev/Code'. Recursos de desarrollo.",
        ),
        # Online generators, converters and PDF tools
        (
            ["generator", "generador", "converter", "convertir",
             "conversor", "online tool", "herramienta online",
             "herramienta gratuita", "free tool", "calculat",
             "calculad", "unir pdf", "merge pdf", "split pdf",
             "comprimir pdf", "compress pdf", "pdf online",
             "cambiar tamaño", "resize", "reducir tamaño",
             "reductor", "reducir mida", "photoshop online",
             "editor online", "en línea", "gratis online",
             "free online"],
            "🔧 Herramientas Online",
            "📂 Sugerencia: Agrupar en 'Herramientas'. Utilidades web.",
        ),
        # E-commerce & Business
        (
            ["tienda online", "online store", "e-commerce", "ecommerce",
             "woocommerce", "shopify", "producto", "product",
             "carrito", "checkout", "envío", "shipping",
             "factura", "invoice", "presupuesto", "cotización"],
            "🛒 Compras y Tiendas",
            "📂 Sugerencia: Agrupar en 'Negocio/Ecommerce'.",
        ),
        # Government & Admin
        (
            ["tramit", "govern", "ajuntament", "ayuntamiento",
             "hacienda", "agencia tributaria", "seguridad social",
             "certificado digital", "dni", "sede electrónica",
             "generalitat", "diputaci", "ministerio", "boe",
             "registro", "notari"],
            "💼 Productividad y Trabajo",
            "📂 Sugerencia: Agrupar en 'Administración/Gobierno'.",
        ),
        # Learning content
        (
            ["tutorial", "aprende", "learn", "curso", "course",
             "lección", "lesson", "guía", "guide", "how to",
             "cómo hacer", "paso a paso", "step by step",
             "introducción a", "introduction to", "beginner",
             "principiante", "masterclass", "academy", "campus",
             "bootcamp", "school", "formación", "training",
             "webinar", "certificación", "certification",
             "networking academy"],
            "📚 Aprendizaje y Cursos",
            "📂 Sugerencia: Agrupar en 'Aprendizaje'. Material educativo.",
        ),
        # Social & Communication
        (
            ["chat", "messenger", "whatsapp", "telegram", "discord",
             "forum", "foro", "comunidad", "community",
             "grupo", "group"],
            "📱 Redes Sociales",
            "📂 Sugerencia: Agrupar en 'Social/Comunidad'.",
        ),
        # Crypto & DeFi
        (
            ["crypto", "cripto", "bitcoin", "ethereum", "blockchain",
             "wallet", "cartera", "token", "nft", "defi",
             "swap", "staking", "mining", "miner", "exchange",
             "usdt", "usdc", "pancakeswap", "uniswap", "metamask",
             "polygon", "solana", "binance", "coinbase", "trading"],
            "🏦 Finanzas y Bancos",
            "🔒 Sugerencia: Agrupar en 'Finanzas/Crypto'.",
        ),
        # Finance & Tax
        (
            ["impuesto", "tax", "declaración", "renta", "hacienda",
             "contabilidad", "accounting", "nómina", "payroll",
             "facturación", "billing", "económic", "economic",
             "inversión", "investment", "bolsa", "stock market",
             "hipoteca", "mortgage", "préstamo", "loan", "seguro",
             "insurance", "presupuesto", "budget"],
            "🏦 Finanzas y Bancos",
            "🔒 Sugerencia: Agrupar en 'Finanzas'.",
        ),
        # Animation & Motion Design
        (
            ["animation", "animación", "motion", "lottie", "gif",
             "sprite", "keyframe", "after effects", "animate",
             "render", "3d model", "blender"],
            "🎨 Diseño",
            "📂 Sugerencia: Agrupar en 'Diseño/Animación'.",
        ),
        # Web checking/analysis tools
        (
            ["checker", "comprobad", "verificad", "validator",
             "analyz", "analizad", "audit", "test online",
             "speed test", "velocidad", "performance",
             "broken link", "dead link", "uptime", "monitor",
             "cms detect", "technology detect", "what cms",
             "site info", "whois", "dns lookup", "ping",
             "traceroute", "port scan"],
            "🔧 Herramientas Online",
            "📂 Sugerencia: Agrupar en 'Herramientas/Análisis Web'.",
        ),
        # Productivity tools (by path/name)
        (
            ["dashboard", "tablero", "panel de control", "administración",
             "configuración", "settings", "account", "cuenta",
             "login", "iniciar sesión", "sign in", "profile",
             "workspace", "espacio de trabajo", "app", "saas",
             "crm", "erp", "project manag", "gestión de proyecto"],
            "💼 Productividad y Trabajo",
            "⭐ Sugerencia: Revisar si se usa a diario.",
        ),
        # Media & Video content
        (
            ["video", "vídeo", "película", "movie", "serie",
             "stream", "directo", "live", "clip", "episod",
             "playlist", "canal", "channel", "podcast",
             "audio", "música", "music", "radio"],
            "🎬 Entretenimiento y Multimedia",
            "📂 Sugerencia: Agrupar en 'Entretenimiento'.",
        ),
    ]

    for keywords, categoria, sugerencia in _content_rules:
        if any(kw in text for kw in keywords):
            return categoria, sugerencia

    # Third pass: domain structure analysis
    return _categorize_by_domain_structure(url)


def _categorize_by_domain_structure(url: str) -> tuple[str, str] | None:
    """Last-resort categorization based on domain TLD, URL path, and common patterns."""
    if not url:
        return None

    url_lower = url.lower()

    try:
        domain = url_lower.split("://")[1].split("/")[0].replace("www.", "")
        path = url_lower.split("://")[1].split("/", 1)[1] if "/" in url_lower.split("://")[1] else ""
    except (IndexError, ValueError):
        return None

    # Government / institutional
    if any(tld in domain for tld in [".gob.", ".gov.", ".edu.", ".ac.",
                                      ".gencat.", ".bcn.", "barcelonactiva",
                                      "paginasamarillas"]):
        return "💼 Productividad y Trabajo", "📂 Institucional/Gobierno."

    # AI-related domains (*.ai TLD + known AI words)
    if (domain.endswith(".ai") or
            any(w in domain for w in ["neural", "model", "doble", "d-id",
                                       "descript", "tts", "voice",
                                       "promeai", "promai"])):
        return "🤖 Inteligencia Artificial", "📂 Herramienta de IA."

    # Dev-related domains
    if domain.endswith(".dev") or domain.endswith(".io") or domain.endswith(".sh"):
        return "💻 Desarrollo y Programación", "📂 Herramienta de desarrollo."

    # Food delivery / local services
    if any(w in domain for w in ["just-eat", "deliveroo", "glovo", "ubereats",
                                  "justeat"]):
        return "🛒 Compras y Tiendas", "📂 Comida/Servicios locales."

    # Color/design/visual tools
    if any(w in domain for w in ["color", "font", "pixel", "design", "art",
                                  "draw", "paint", "photo", "pixton",
                                  "comic", "ilustra"]):
        return "🎨 Diseño", "📂 Herramienta de diseño."

    # Analytics / marketing / sales tools
    if any(w in domain for w in ["analytics", "metric", "hotjar", "drip",
                                  "lead", "sales", "market", "flippa",
                                  "wot", "safety", "security"]):
        return "💻 Desarrollo y Programación", "📂 Marketing/Analytics."

    # Downloader / converter / online tools
    if (any(w in domain for w in ["download", "convert", "compress", "cut",
                                   "merge", "split", "resize", "translator",
                                   "traductor", "contador", "editor",
                                   "pdf", "doc", "lorca"]) or
            "tools" in path or "tool" in path):
        return "🔧 Herramientas Online", "📂 Herramienta online."

    # File transfer
    if any(w in domain for w in ["ydray", "wetransfer", "sendspace",
                                  "mediafire", "mega.nz"]):
        return "🔧 Herramientas Online", "📂 Transferencia de archivos."

    # Scientific / academic
    if any(w in domain for w in ["pubmed", "scholar", "arxiv", "researchgate",
                                  "academia.edu", "scielo"]):
        return "📚 Aprendizaje y Cursos", "📂 Artículo científico."

    # Money / finance keywords in domain
    if any(w in domain for w in ["money", "invest", "finanz", "crypto",
                                  "coin", "trade", "bank"]):
        return "🏦 Finanzas y Bancos", "📂 Finanzas."

    # .org / .info domains → usually informational
    if domain.endswith(".org") or domain.endswith(".info"):
        return "📰 Noticias e Información", "📂 Organización/Información."

    # SaaS / app domains with dashboard/app paths
    if any(p in path for p in ["dashboard", "app", "admin", "panel",
                                "settings", "account"]):
        return "💼 Productividad y Trabajo", "📂 Aplicación web."

    # Pricing / buy pages suggest commercial tools
    if any(p in path for p in ["pricing", "plans", "buy", "checkout",
                                "subscribe"]):
        return "🛒 Compras y Tiendas", "📂 Servicio de pago."

    # .cat / .es regional → local services / productivity
    if domain.endswith(".cat") or domain.endswith(".page"):
        return "💼 Productividad y Trabajo", "📂 Servicio local/personal."

    return None


def _fetch_page_meta(url: str, timeout: int = 5) -> str:
    """Fetch the <head> of a URL and extract title + meta description.

    Only downloads the first ~8KB to avoid loading full pages.
    Returns concatenated title + description text, or empty string on failure.
    """
    import urllib.request
    import urllib.error
    import ssl

    if not url or not url.startswith("http"):
        return ""

    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"},
        )
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            # Read only first 8KB — enough for <head>
            raw = resp.read(8192)
            try:
                html = raw.decode("utf-8", errors="ignore")
            except Exception:
                html = raw.decode("latin-1", errors="ignore")

        # Extract <title>
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else ""

        # Extract meta description
        desc_match = re.search(
            r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']',
            html, re.IGNORECASE | re.DOTALL,
        )
        if not desc_match:
            desc_match = re.search(
                r'<meta\s+content=["\'](.*?)["\']\s+name=["\']description["\']',
                html, re.IGNORECASE | re.DOTALL,
            )
        desc = desc_match.group(1).strip() if desc_match else ""

        # Extract meta keywords
        kw_match = re.search(
            r'<meta\s+name=["\']keywords["\']\s+content=["\'](.*?)["\']',
            html, re.IGNORECASE | re.DOTALL,
        )
        keywords = kw_match.group(1).strip() if kw_match else ""

        return f"{title} {desc} {keywords}".strip()
    except Exception:
        return ""


def _get_deep_cache_path() -> str:
    """Return path to the deep categorization cache file."""
    cache_dir = os.path.join(os.path.expanduser("~"), ".cleanacelerai")
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, "deep_cache.json")


def _load_deep_cache() -> dict[str, dict[str, str]]:
    """Load cached deep categorization results. Returns {url: {category, subcategory}}."""
    path = _get_deep_cache_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_deep_cache(cache: dict[str, dict[str, str]]) -> None:
    """Save deep categorization cache to disk."""
    path = _get_deep_cache_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)


def apply_deep_cache(bookmarks: list[Bookmark]) -> int:
    """Apply cached deep categorization results to bookmarks. Returns count applied."""
    cache = _load_deep_cache()
    if not cache:
        return 0
    applied = 0
    for bm in bookmarks:
        if "Generales" not in bm.category:
            continue
        cached = cache.get(bm.url)
        if cached:
            bm.category = cached["category"]
            bm.subcategory = cached.get("subcategory", "")
            applied += 1
    return applied


def deep_categorize_bookmarks(
    bookmarks: list[Bookmark],
    progress_cb: Callable[[int], None] | None = None,
    max_workers: int = 8,
) -> int:
    """Fetch uncategorized bookmark pages and categorize by their content.

    Modifies bookmarks in-place and saves results to a persistent cache file.
    Skips URLs that were already cached (won't re-fetch).

    Args:
        bookmarks: List of Bookmark objects (modified in-place).
        progress_cb: Optional callback receiving progress percentage (0-100).
        max_workers: Number of parallel fetch threads.

    Returns:
        Number of bookmarks that were successfully re-categorized.
    """
    import concurrent.futures

    cache = _load_deep_cache()

    # Apply cached results first
    for bm in bookmarks:
        if "Generales" in bm.category and bm.url in cache:
            bm.category = cache[bm.url]["category"]
            bm.subcategory = cache[bm.url].get("subcategory", "")

    # Only fetch URLs not in cache
    uncategorized = [
        b for b in bookmarks
        if "Generales" in b.category and b.url not in cache
    ]
    if not uncategorized:
        if progress_cb:
            progress_cb(100)
        return 0

    total = len(uncategorized)
    recategorized = 0
    completed = 0

    def process_one(bm: Bookmark) -> tuple[Bookmark, str]:
        meta = _fetch_page_meta(bm.url, timeout=5)
        return bm, meta

    def process_with_status(bm: Bookmark) -> tuple[Bookmark, str, int]:
        """Fetch URL and return (bookmark, meta_text, http_status_code)."""
        import urllib.request
        import urllib.error
        import ssl

        if not bm.url or not bm.url.startswith("http"):
            return bm, "", 0

        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(
                bm.url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"},
            )
            with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
                status = resp.status
                raw = resp.read(8192)
                try:
                    html = raw.decode("utf-8", errors="ignore")
                except Exception:
                    html = raw.decode("latin-1", errors="ignore")

            title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip() if title_match else ""
            desc_match = re.search(
                r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']',
                html, re.IGNORECASE | re.DOTALL,
            )
            if not desc_match:
                desc_match = re.search(
                    r'<meta\s+content=["\'](.*?)["\']\s+name=["\']description["\']',
                    html, re.IGNORECASE | re.DOTALL,
                )
            desc = desc_match.group(1).strip() if desc_match else ""
            return bm, f"{title} {desc}".strip(), status

        except urllib.error.HTTPError as e:
            return bm, "", e.code
        except Exception:
            return bm, "", 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_with_status, b): b for b in uncategorized}
        for future in concurrent.futures.as_completed(futures):
            completed += 1
            try:
                bm, meta, status = future.result()

                # Mark dead URLs
                if status in (404, 410) or status == 0:
                    bm.category = "💀 Enlace Muerto"
                    bm.suggestion = "⚠️ Esta página no existe o no responde. Se recomienda eliminar."
                    bm.subcategory = ""
                    cache[bm.url] = {"category": bm.category, "subcategory": ""}
                    recategorized += 1
                elif meta:
                    combined_name = f"{bm.name} {meta}"
                    result = categorize_by_content(combined_name, bm.url)
                    if result:
                        bm.category, bm.suggestion = result
                        bm.subcategory = subcategorize_url(bm.url, bm.category)
                        cache[bm.url] = {
                            "category": bm.category,
                            "subcategory": bm.subcategory,
                        }
                        recategorized += 1
                    else:
                        cache[bm.url] = {"category": bm.category, "subcategory": ""}
                else:
                    cache[bm.url] = {"category": bm.category, "subcategory": ""}
            except Exception:
                pass

            if progress_cb and total > 0:
                progress_cb(int(completed / total * 100))

    _save_deep_cache(cache)
    return recategorized


def subcategorize_url(url: str, category: str) -> str:
    """
    Return a subcategory name for a URL within its main category.

    Uses domain matching to assign subcategories for IA, Desarrollo,
    and Entretenimiento. Other categories return empty string (no subcategory).

    Args:
        url: The bookmark URL.
        category: The main category label from categorize_url().

    Returns:
        Subcategory name, or empty string if none applies.
    """
    if not url:
        return ""

    url_lower = url.lower()

    if category == "🤖 Inteligencia Artificial":
        # Chatbots
        chatbot_domains = [
            "chatgpt.com", "chat.openai.com", "claude.ai",
            "gemini.google.com", "copilot.microsoft.com", "poe.com",
            "perplexity.ai",
        ]
        if any(d in url_lower for d in chatbot_domains):
            return "Chatbots"

        # Modelos y Spaces (check before generic huggingface)
        if "huggingface.co/spaces" in url_lower or "huggingface.co/models" in url_lower:
            return "Modelos y Spaces"

        # Aprendizaje IA
        aprendizaje_domains = ["huggingface.co/learn", "linkedin.com/learning"]
        if any(d in url_lower for d in aprendizaje_domains) or "courses" in url_lower:
            return "Aprendizaje IA"

        # Everything else in IA
        return "Herramientas IA"

    if category == "💻 Desarrollo y Programación":
        # Repos y Código
        repo_domains = ["github.com", "gitlab.com", "bitbucket.org"]
        if any(d in url_lower for d in repo_domains):
            return "Repos y Codigo"

        # Documentación
        doc_patterns = ["docs.", "developer.", "mdn", "w3schools", "microsoft.com/docs"]
        if any(p in url_lower for p in doc_patterns):
            return "Documentacion"

        # Paquetes
        pkg_domains = ["npmjs.com", "pypi.org"]
        if any(d in url_lower for d in pkg_domains):
            return "Paquetes"

        # Everything else in Desarrollo
        return "Herramientas Dev"

    if category == "🎬 Entretenimiento y Multimedia":
        # Videos
        video_domains = ["youtube.com", "vimeo.com", "twitch.tv"]
        if any(d in url_lower for d in video_domains):
            return "Videos"

        # Música
        music_domains = ["spotify.com", "soundcloud"]
        if any(d in url_lower for d in music_domains):
            return "Musica"

        # Streaming
        streaming_domains = ["netflix", "primevideo", "disney"]
        if any(d in url_lower for d in streaming_domains):
            return "Streaming"

        return ""

    # Other categories: no subcategory
    return ""


def load_bookmarks(bookmark_file: str) -> list[Bookmark]:
    """
    Load and categorize all bookmarks from a Chromium Bookmarks JSON file.

    Args:
        bookmark_file: Absolute path to the Bookmarks JSON file.

    Returns:
        List of Bookmark objects with category and suggestion populated.

    Raises:
        PermissionError: If the file cannot be read.
        json.JSONDecodeError: If the file is malformed.
        OSError: For other I/O errors.
    """
    with open(bookmark_file, "r", encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)

    todos: list[dict[str, str]] = []
    for raiz in data.get("roots", {}).values():
        if isinstance(raiz, dict):
            todos.extend(_extract_nodes(raiz, str(raiz.get("name", "Raíz"))))

    # Load deep categorization cache for persistent results
    deep_cache = _load_deep_cache()

    bookmarks: list[Bookmark] = []
    for m in todos:
        # Check deep cache first (persistent results from web fetching)
        cached = deep_cache.get(m["url"])
        if cached and "Generales" not in cached.get("category", "Generales"):
            categoria = cached["category"]
            sugerencia = ""
            subcategoria = cached.get("subcategory", "")
        else:
            categoria, sugerencia = categorize_url(m["url"])
            # Second pass: if domain-based categorization failed, try content analysis
            if "Generales" in categoria or "Otros" in categoria:
                content_result = categorize_by_content(m["name"], m["url"])
                if content_result:
                    categoria, sugerencia = content_result
            subcategoria = subcategorize_url(m["url"], categoria)
        bookmarks.append(
            Bookmark(
                id=m["id"],
                name=m["name"],
                url=m["url"],
                path=m["path"],
                category=categoria,
                subcategory=subcategoria,
                suggestion=sugerencia,
            )
        )

    return bookmarks


# ── Category → clean folder name mapping ──────────────────────────────────

CATEGORY_FOLDER_MAP: dict[str, str] = {
    "💻 Desarrollo y Programación": "Desarrollo",
    "🤖 Inteligencia Artificial": "IA",
    "🎬 Entretenimiento y Multimedia": "Entretenimiento",
    "📱 Redes Sociales": "Redes Sociales",
    "💼 Productividad y Trabajo": "Productividad",
    "🛒 Compras y Tiendas": "Compras",
    "📰 Noticias e Información": "Noticias",
    "🏦 Finanzas y Bancos": "Finanzas",
    "🌐 Sitios Web Generales": "Otros",
    "📚 Aprendizaje y Cursos": "Aprendizaje",
    "🎨 Diseño": "Diseño",
    "🔧 Herramientas Online": "Herramientas",
    "📁 Otros / Desconocido": "Otros",
    "💀 Enlace Muerto": "Enlaces Muertos",
}

# ── Patterns for clean_bookmark_name ──────────────────────────────────────

_SITE_SUFFIXES = re.compile(
    r"\s*[\-–—|·:]\s*("
    r"YouTube|Medium|Stack Overflow|Wikipedia|GitHub|LinkedIn|"
    r"Google Search|Google|Reddit|Facebook|Twitter|X|"
    r"Amazon|eBay|Netflix|Twitch|Spotify|Pinterest|"
    r"Udemy|Coursera|Platzi|freeCodeCamp|W3Schools|MDN Web Docs|"
    r"Figma|Canva|Dribbble|Behance|"
    r"npm|Dev Community|DEV Community|Stack Exchange|"
    r"Microsoft Learn|Microsoft Docs|"
    r"Hacker News|TechCrunch|The Verge|"
    r"Adobe Express|FlexClip|PageSpeed|Pixlr|Pexels|Pixabay|"
    r"Unsplash|Chrome Web Store|Herramientas PageSpeed|"
    r"Gmail|Outlook|Bitly|Notion|Trello"
    r")\s*$",
    re.IGNORECASE,
)

_COMMON_PREFIXES = re.compile(
    r"^(Home\s*[-–|:]\s*|Welcome to\s+|Inicio\s*[-–|:]\s*|"
    r"Sign in\s*[-–|:]\s*|Log in\s*[-–|:]\s*)",
    re.IGNORECASE,
)

_EMOJI_PATTERN = re.compile(
    r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
    r"\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U0000FE00-\U0000FE0F"
    r"\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF"
    r"\U00002600-\U000026FF\U00002700-\U000027BF]+",
)

_TRAILING_SEPARATORS = re.compile(r"[\s\-–|·:]+$")

# Chatbot/tool prefixes: "ChatGPT - ", "ChatGPT — ", "Gemini - ", "Claude - ", etc.
_CHATBOT_PREFIXES = re.compile(
    r"^(ChatGPT|Gemini|Claude|Copilot|Perplexity)\s*[\-–—:|]\s*",
    re.IGNORECASE,
)

# Bad HuggingFace auto-translations
_HF_BAD_TRANSLATIONS = [
    (re.compile(r"Abrazando la cara", re.IGNORECASE), "HuggingFace"),
    (re.compile(r"Abrazo de cara", re.IGNORECASE), "HuggingFace"),
    (re.compile(r"un espacio para abrazar la cara de[^\"]*", re.IGNORECASE), ""),
    (re.compile(r"A Hugging Face Space by[^\"]*", re.IGNORECASE), ""),
    (re.compile(r":\s*un espacio para\b[^\"]*", re.IGNORECASE), ""),
]

# LinkedIn Learning cleanup
_LINKEDIN_LEARNING = re.compile(r"\s*\|\s*LinkedIn Learning\s*$", re.IGNORECASE)

# "100% Free " prefix
_FREE_PREFIX = re.compile(r"^100%\s*Free\s+", re.IGNORECASE)

# URL query artifacts that leak into names
_URL_ARTIFACTS = re.compile(r"[?&]\w+=\S+")

# Email addresses embedded in bookmark names
# Only consume leading separators, not trailing ones (so "- Gmail" stays for suffix removal)
_EMAIL_PATTERN = re.compile(r"\s*[-–—]*\s*[\w.+-]+@[\w-]+\.[\w.-]+")

# Generic separator cleaning: " | SiteName" or " - SiteName" at end
# Matches separator + 1-3 capitalized/short words that look like a site name
_GENERIC_SITE_SUFFIX = re.compile(
    r"\s*[\-–—|]\s*[A-Z][\w]*(?:\s+[A-Z][\w]*)?\s*$",
)


def clean_bookmark_name(name: str, url: str) -> str:
    """
    Remove common clutter from bookmark names to make them short and concise.

    Args:
        name: The original bookmark name.
        url: The bookmark URL (used as fallback for empty names).

    Returns:
        A cleaned, truncated bookmark name (max 40 chars).
    """
    cleaned = name.strip()

    # If name is empty or just the URL, extract from domain
    if not cleaned or cleaned == url:
        cleaned = _name_from_url(url)

    # Remove emojis and excessive special characters
    cleaned = _EMOJI_PATTERN.sub("", cleaned).strip()

    # Remove chatbot/tool prefixes (e.g. "ChatGPT - Resumen de PDF" → "Resumen de PDF")
    cleaned = _CHATBOT_PREFIXES.sub("", cleaned).strip()

    # Fix bad HuggingFace translations
    for pattern, replacement in _HF_BAD_TRANSLATIONS:
        cleaned = pattern.sub(replacement, cleaned).strip()

    # Remove "100% Free " prefix
    cleaned = _FREE_PREFIX.sub("", cleaned).strip()

    # Clean LinkedIn Learning suffix
    cleaned = _LINKEDIN_LEARNING.sub("", cleaned).strip()

    # Remove URL query artifacts
    cleaned = _URL_ARTIFACTS.sub("", cleaned).strip()

    # Remove email addresses (e.g. "Destacados - jose190272@gmail.com - Gmail")
    cleaned = _EMAIL_PATTERN.sub(" ", cleaned).strip()

    # Remove common prefixes FIRST (before suffixes)
    cleaned = _COMMON_PREFIXES.sub("", cleaned).strip()

    # Remove site suffixes (may need multiple passes for stacked suffixes)
    for _ in range(3):
        prev = cleaned
        cleaned = _SITE_SUFFIXES.sub("", cleaned).strip()
        if cleaned == prev:
            break

    # Generic separator cleaning: if after specific suffixes there is still
    # " | Word" or " - Word" at the end that looks like a site name, remove it
    cleaned = _GENERIC_SITE_SUFFIX.sub("", cleaned).strip()

    # Remove trailing separators
    cleaned = _TRAILING_SEPARATORS.sub("", cleaned).strip()

    # Final fallback
    if not cleaned:
        cleaned = _name_from_url(url)

    # Truncate to 40 chars — cut at word boundary if possible
    if len(cleaned) > 40:
        truncated = cleaned[:37]
        last_space = truncated.rfind(" ")
        if last_space > 20:
            cleaned = truncated[:last_space] + "..."
        else:
            cleaned = truncated + "..."

    return cleaned


def _name_from_url(url: str) -> str:
    """Extract a readable name from a URL's domain."""
    try:
        # Remove protocol
        domain = url.split("://", 1)[-1].split("/", 1)[0]
        # Remove www.
        domain = domain.removeprefix("www.")
        # Take domain name without TLD
        parts = domain.split(".")
        if len(parts) >= 2:
            return parts[0].capitalize()
        return domain.capitalize()
    except Exception:
        return "Sin nombre"


def organize_bookmarks_into_folders(
    bookmark_file: str,
    bookmarks: list[Bookmark],
) -> int:
    """
    Organize bookmarks into category folders in the browser's Bookmarks JSON file.

    REBUILD approach: extracts ALL url bookmarks from the entire tree,
    categorizes them, and rebuilds the bookmark_bar from scratch with
    clean category folders. This is robust against ID mismatches from
    Chrome Sync.

    Args:
        bookmark_file: Absolute path to the Chromium Bookmarks file.
        bookmarks: List of Bookmark objects (used for category mapping by URL).

    Returns:
        Count of bookmarks organized.
    """
    # Create backup before modifying
    backup_path = bookmark_file + f"_Cleanacelerai_Backup_{int(time.time())}.json"
    shutil.copy2(bookmark_file, backup_path)

    with open(bookmark_file, "r", encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)

    bookmark_bar = data.get("roots", {}).get("bookmark_bar")
    if not bookmark_bar or not isinstance(bookmark_bar, dict):
        return 0

    # Step 1: Extract ALL url bookmarks from the entire tree (flatten)
    all_urls: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    def _collect_urls(nodo: Any) -> None:
        if not isinstance(nodo, dict):
            return
        if nodo.get("type") == "url" and nodo.get("url"):
            url = nodo["url"]
            if url not in seen_urls:
                seen_urls.add(url)
                all_urls.append({
                    "name": nodo.get("name", ""),
                    "url": url,
                    "date_added": nodo.get("date_added", "0"),
                })
        elif nodo.get("type") == "folder":
            for child in nodo.get("children", []):
                _collect_urls(child)

    # Collect from all roots (bookmark_bar, other, synced)
    for raiz in data.get("roots", {}).values():
        if isinstance(raiz, dict):
            _collect_urls(raiz)

    if not all_urls:
        return 0

    # Step 2: Build category lookup from in-memory bookmarks (by URL)
    url_to_bookmark: dict[str, Bookmark] = {}
    for b in bookmarks:
        if b.url not in url_to_bookmark:
            url_to_bookmark[b.url] = b

    # Step 3: Categorize all collected URLs
    categorized: list[tuple[dict[str, str], str, str, str]] = []
    for entry in all_urls:
        url = entry["url"]
        bm = url_to_bookmark.get(url)
        if bm:
            cat = bm.category
            subcat = bm.subcategory
            name = clean_bookmark_name(bm.original_name or bm.name or entry["name"], url)
        else:
            # Not in our loaded list, categorize fresh
            cat, _ = categorize_url(url)
            content_result = categorize_by_content(entry["name"], url)
            if ("Generales" in cat or "Otros" in cat) and content_result:
                cat = content_result[0]
            subcat = subcategorize_url(url, cat)
            name = clean_bookmark_name(entry["name"], url)

        folder_name = CATEGORY_FOLDER_MAP.get(cat, "Otros")
        categorized.append((entry, folder_name, subcat, name))

    # Step 4: Count subcategories for subfolder decisions
    subcat_counts: Counter[tuple[str, str]] = Counter()
    for _, folder_name, subcat, _ in categorized:
        if subcat:
            subcat_counts[(folder_name, subcat)] += 1

    # Step 5: Build new folder structure
    next_id = _find_max_id(data) + 1
    new_folders: dict[str, dict[str, Any]] = {}
    sub_folders: dict[str, dict[str, Any]] = {}

    def _get_folder(folder_name: str) -> dict[str, Any]:
        nonlocal next_id
        if folder_name not in new_folders:
            next_id += 1
            new_folders[folder_name] = {
                "children": [],
                "date_added": "0",
                "date_last_used": "0",
                "date_modified": "0",
                "id": str(next_id),
                "name": folder_name,
                "type": "folder",
            }
        return new_folders[folder_name]

    def _get_subfolder(folder_name: str, subcat: str) -> dict[str, Any]:
        nonlocal next_id
        key = f"{folder_name}/{subcat}"
        if key not in sub_folders:
            next_id += 1
            sf: dict[str, Any] = {
                "children": [],
                "date_added": "0",
                "date_last_used": "0",
                "date_modified": "0",
                "id": str(next_id),
                "name": subcat,
                "type": "folder",
            }
            _get_folder(folder_name)["children"].append(sf)
            sub_folders[key] = sf
        return sub_folders[key]

    organized_count = 0
    for entry, folder_name, subcat, name in categorized:
        # Decide target: subfolder if 3+ items, else main folder
        if subcat and subcat_counts[(folder_name, subcat)] >= 3:
            target = _get_subfolder(folder_name, subcat)
        else:
            target = _get_folder(folder_name)

        next_id += 1
        target["children"].append({
            "date_added": entry.get("date_added", "0"),
            "date_last_used": "0",
            "id": str(next_id),
            "name": name,
            "type": "url",
            "url": entry["url"],
        })
        organized_count += 1

    # Step 6: Replace bookmark_bar children entirely with new folders
    # Preserve order: known categories first, then "Otros"
    folder_order = [
        "Productividad", "Desarrollo", "IA", "Diseño", "Herramientas",
        "Aprendizaje", "Entretenimiento", "Redes Sociales", "Noticias",
        "Compras", "Finanzas", "Otros",
    ]
    ordered_children: list[dict[str, Any]] = []
    for fname in folder_order:
        if fname in new_folders:
            ordered_children.append(new_folders.pop(fname))
    # Any remaining folders not in our order
    for fname, folder in new_folders.items():
        ordered_children.append(folder)

    bookmark_bar["children"] = ordered_children

    # Clear other roots to avoid duplicates (synced bookmarks, etc.)
    for key, raiz in data.get("roots", {}).items():
        if isinstance(raiz, dict) and key != "bookmark_bar":
            if "children" in raiz:
                raiz["children"] = []

    # Write back
    _write_bookmarks(bookmark_file, data)
    return organized_count


def _write_bookmarks(bookmark_file: str, data: dict[str, Any]) -> None:
    """Write bookmark data and sync the .bak file so Chrome doesn't restore old version."""
    content = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

    with open(bookmark_file, "w", encoding="utf-8") as f:
        f.write(content)

    # Overwrite .bak with the same content so Chrome can't restore the old version
    bak_file = bookmark_file + ".bak"
    with open(bak_file, "w", encoding="utf-8") as f:
        f.write(content)

    # Clean up old Cleanacelerai backup files (keep only the latest)
    import glob
    backup_dir = os.path.dirname(bookmark_file)
    pattern = os.path.join(backup_dir, "Bookmarks_Cleanacelerai_*")
    old_backups = sorted(glob.glob(pattern))
    for old in old_backups[:-1]:  # Keep only the most recent
        try:
            os.remove(old)
        except OSError:
            pass


def _find_max_id(data: Any) -> int:
    """Find the maximum numeric bookmark ID in the JSON structure."""
    max_val = 0

    def _walk(nodo: Any) -> None:
        nonlocal max_val
        if isinstance(nodo, dict):
            try:
                nid = int(nodo.get("id", "0"))
                if nid > max_val:
                    max_val = nid
            except (ValueError, TypeError):
                pass
            for v in nodo.values():
                _walk(v)
        elif isinstance(nodo, list):
            for item in nodo:
                _walk(item)

    _walk(data)
    return max_val


def delete_bookmarks_by_id(
    bookmark_file: str,
    ids_to_delete: list[str],
) -> None:
    """
    Remove bookmarks by ID from a Chromium Bookmarks file (in-place).

    Creates a .json backup before modifying.

    Args:
        bookmark_file: Absolute path to the Bookmarks file.
        ids_to_delete: List of bookmark ID strings to remove.

    Raises:
        PermissionError: If the file is locked (browser open).
        OSError: For other I/O errors.
    """
    ids_set = set(ids_to_delete)

    # Backup first
    backup_path = bookmark_file + "_Cleanacelerai_Backup.json"
    shutil.copy2(bookmark_file, backup_path)

    with open(bookmark_file, "r", encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)

    def _remove(nodo: Any) -> None:
        if isinstance(nodo, dict) and "children" in nodo:
            nodo["children"] = [c for c in nodo["children"] if c.get("id") not in ids_set]
            for hijo in nodo["children"]:
                _remove(hijo)

    for raiz in data.get("roots", {}).values():
        _remove(raiz)

    # Write back (also syncs .bak to prevent Chrome from restoring old version)
    _write_bookmarks(bookmark_file, data)
