# --- PALETA DE COLORES (Dashboard oscuro) ---
COLOR_BG = "#111827"
COLOR_CARD = "#1F2937"
COLOR_BORDER = "#374151"
COLOR_TEXT_MAIN = "#F3F4F6"
COLOR_TEXT_MUTED = "#9CA3AF"
COLOR_ACCENT = "#3B82F6"
COLOR_SUCCESS = "#10B981"
COLOR_WARNING = "#F59E0B"
COLOR_DANGER = "#EF4444"

# --- MOTOR DE PROTECCIÓN ---
CARPETAS_SISTEMA: set[str] = {
    'windows', 'program files', 'archivos de programa',
    'program files (x86)', 'appdata', 'programdata', 'boot',
    'system volume information', 'perflogs', 'winsxs',
    '$recycle.bin', 'default', 'documents and settings',
}

CARPETAS_PERFIL_PROTEGIDAS: set[str] = {
    'desktop', 'documents', 'downloads', 'pictures', 'music',
    'videos', 'saved games', 'searches', 'links', 'contacts',
    'favorites', 'onedrive', 'dropbox',
}

DOTFILES_CRITICOS: set[str] = {
    '.vscode', '.ssh', '.git', '.conda', '.docker', '.azure',
    '.aws', '.config', '.local', '.cargo', '.rustup', '.ollama',
}

EXTENSIONES_SISTEMA: tuple[str, ...] = (
    '.sys', '.dll', '.dat', '.regtrans-ms', '.blf', '.ini',
    '.db', '.tlb', '.cpl', '.msc', '.msi', '.cab',
)

ARCHIVOS_PROHIBIDOS: set[str] = {
    'ntuser.dat', 'desktop.ini', 'thumbs.db',
    'pagefile.sys', 'hiberfil.sys', 'swapfile.sys', 'dumpstack.log',
}

# --- Intelligent Chaos Advisor ---
from pathlib import Path

IMAGE_EXTENSIONS: tuple[str, ...] = (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff")
DOCUMENT_EXTENSIONS: tuple[str, ...] = (".pdf",)

MODEL_CACHE_DIR = Path("D:/Cleanacelerai_models")

# Keywords for heuristic document classification (Spanish + English)
DOC_KEYWORDS: dict[str, list[str]] = {
    "FACTURA": ["factura", "invoice", "nif", "cif", "iva", "subtotal", "importe", "total a pagar", "número de factura", "invoice number", "tax"],
    "RECIBO": ["recibo", "receipt", "pagado", "comprobante de pago", "transferencia", "payment confirmation"],
    "CONTRATO": ["contrato", "contract", "cláusula", "clause", "firmante", "partes contratantes", "terms and conditions", "agreement"],
    "TUTORIAL": ["tutorial", "paso a paso", "step by step", "cómo hacer", "how to", "guía", "guide", "aprende", "learn", "ejemplo", "example"],
    "LIBRO": ["capítulo", "chapter", "prólogo", "prologue", "índice", "table of contents", "isbn", "editorial", "publisher", "autor", "author"],
    "MANUAL": ["manual", "instrucciones", "instructions", "especificaciones", "specifications", "instalación", "installation", "configuración", "setup"],
    "CARTA": ["estimado", "dear", "atentamente", "sincerely", "cordialmente", "regards", "a quien corresponda", "to whom it may concern"],
    "INFORME": ["informe", "report", "resumen ejecutivo", "executive summary", "conclusiones", "conclusions", "análisis", "analysis", "resultados", "results"],
    "ACADÉMICO": ["tesis", "thesis", "bibliografía", "bibliography", "abstract", "resumen", "universidad", "university", "investigación", "research", "hipótesis", "hypothesis"],
}

# --- Deep Cleaner ---
DEEP_CLEAN_RISK_COLORS: dict[str, str] = {
    "SISTEMA": COLOR_DANGER,
    "CRITICO": "#F97316",
    "ACTIVO": COLOR_WARNING,
    "CACHE": COLOR_SUCCESS,
    "VACIO": COLOR_TEXT_MUTED,
}

DEEP_CLEAN_BUNDLE_ICONS: dict[str, str] = {
    "Herramientas de IA": "🤖",
    "Editores y Desarrollo": "💻",
    "Cache y Temporales": "🗑️",
    "Sistema Windows": "🪟",
    "Desconocido": "❓",
}

SYSTEM_ROOT_PROTECTED: set[str] = {
    "windows", "program files", "program files (x86)",
    "archivos de programa", "users", "programdata",
    "perflogs", "recovery", "$recycle.bin",
    "system volume information", "boot",
    "documents and settings",
}
