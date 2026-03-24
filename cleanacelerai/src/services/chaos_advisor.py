"""Service: analyse chaotic folders and suggest actions."""
from __future__ import annotations

import os
from dataclasses import dataclass

from ..domain.models import RiskLevel
from ..domain.risk_evaluator import evaluate_file_risk


@dataclass
class AdvisorEntry:
    """A single entry in the chaos advisor analysis."""
    path: str
    name: str
    is_dir: bool
    risk: RiskLevel
    risk_detail: str
    tipo: str
    detalles: str
    accion: str
    tag: str  # Treeview tag name


def inspect_folder(path: str) -> str:
    """
    Heuristically inspect a folder's content type.

    Args:
        path: Absolute path to the folder.

    Returns:
        Human-readable description of the folder's content.
    """
    try:
        archivos = os.listdir(path)
        if not archivos:
            return "Carpeta vacía."

        exts = [
            os.path.splitext(f)[1].lower()
            for f in archivos
            if os.path.isfile(os.path.join(path, f))
        ]
        dirs = [f for f in archivos if os.path.isdir(os.path.join(path, f))]

        if "package.json" in archivos or "node_modules" in dirs:
            return "💻 Proyecto Web (Node.js/React)"
        if "venv" in dirs or "env" in dirs:
            return "🐍 Proyecto Python (con Venv)"
        if ".git" in dirs:
            return "⚙️ Repositorio Git"
        if any(e in [".jpg", ".png", ".mp4"] for e in exts):
            return "📸 Contiene Multimedia"
        if any(e in [".pdf", ".docx", ".xlsx"] for e in exts):
            return "📄 Contiene Documentos"

        return f"📁 Mixto ({len(archivos)} elementos)"
    except (PermissionError, OSError):
        return "🔒 Sin permisos"


def analyze_folder(
    carpeta: str,
    protected_keywords: list[str] | None = None,
    protected_folders: list[str] | None = None,
) -> list[AdvisorEntry]:
    """
    Analyse all items in a folder and return advisor entries.

    Args:
        carpeta: Absolute path to the folder to analyse.
        protected_keywords: User-defined protection keywords.
        protected_folders: User-defined protected folder paths.

    Returns:
        List of AdvisorEntry for each item found.

    Raises:
        PermissionError: If the folder cannot be read.
        FileNotFoundError: If the folder no longer exists.
        OSError: For other I/O errors.
    """
    if protected_keywords is None:
        protected_keywords = []
    if protected_folders is None:
        protected_folders = []

    entries: list[AdvisorEntry] = []
    elementos = os.listdir(carpeta)

    for nombre in elementos:
        ruta_completa = os.path.join(carpeta, nombre)
        es_dir = os.path.isdir(ruta_completa)
        risk = evaluate_file_risk(ruta_completa, protected_keywords, protected_folders)

        tipo = ""
        accion = ""
        tag = ""
        detalles = ""
        risk_detail = str(risk.value)

        if es_dir:
            if risk == RiskLevel.SYSTEM or risk == RiskLevel.CRITICAL:
                tipo = "Carpeta Sistema"
                accion = "🔴 PROHIBIDO TOCAR (Romperás Windows)."
                tag = "notocar"
            elif risk == RiskLevel.PERSONAL:
                tipo = "Carpeta Perfil"
                accion = "⚠️ PROTEGIDA. No la muevas con programas. Úsala en C:."
                tag = "perfil"
            elif risk == RiskLevel.DOTFILE:
                tipo = "Configuración (Tuberías)"
                accion = "🛡️ ESCUDO ACTIVO. Desconfigurarás tus herramientas."
                tag = "notocar"
            else:
                tipo = "Carpeta Proyecto"
                accion = "📦 MOVER A DISCO D: (Mis_Proyectos)."
                tag = "mover"
                detalles = inspect_folder(ruta_completa)
        else:
            if risk in (RiskLevel.SYSTEM, RiskLevel.CRITICAL):
                tipo = "Archivo Sistema (.dll, .ini, .sys)"
                accion = "🔴 PROHIBIDO TOCAR. Romperás Windows."
                tag = "notocar"
            elif risk == RiskLevel.DOTFILE:
                tipo = "Configuración (Tuberías)"
                accion = "🛡️ ESCUDO ACTIVO. Desconfigurarás herramientas."
                tag = "notocar"
            elif nombre.lower().endswith((".exe", ".msi")):
                tipo = "Instalador"
                accion = "🗑️ BORRAR o MOVER (Instaladores antiguos)."
                tag = "borrar"
            elif nombre.lower().endswith((".backup", ".bak", ".tmp", ".log")):
                tipo = "Basura"
                accion = "🗑️ BORRAR."
                tag = "borrar"
            else:
                tipo = "Archivo Personal"
                accion = "📦 MOVER A DISCO D: (Organízalo)."
                tag = "mover"
                try:
                    detalles = f"{os.path.getsize(ruta_completa) / (1024 * 1024):.2f} MB"
                except (OSError, PermissionError):
                    detalles = "Tamaño desconocido"

        entries.append(
            AdvisorEntry(
                path=ruta_completa,
                name=nombre,
                is_dir=es_dir,
                risk=risk,
                risk_detail=risk_detail,
                tipo=tipo,
                detalles=detalles,
                accion=accion,
                tag=tag,
            )
        )

    return entries


def explain_element(name: str, tipo: str) -> str:
    """
    Return a forensic explanation text for a given file/folder type.

    Args:
        name: File or folder name.
        tipo: Category string from the advisor.

    Returns:
        Spanish explanation string.
    """
    if "dll" in name.lower() or "sys" in name.lower():
        return (
            "Este es un 'Librería de Enlace Dinámico' (.dll) o un 'Driver de Sistema' (.sys). "
            "Contiene instrucciones vitales para que Windows sepa cómo comunicarse con tu hardware "
            "(tarjeta gráfica, ratón, etc.). Si lo borras o lo mueves, es muy probable que Windows "
            "deje de arrancar o que dejen de funcionar los programas que dependen de él. "
            "¡La IA lo ha protegido automáticamente para que no lo toques!"
        )
    if "ini" in name.lower():
        return (
            "Este es un archivo de 'Inicialización' (.ini). Contiene las configuraciones de arranque "
            "de un programa o de una carpeta específica (como desktop.ini). Si lo borras, el programa "
            "asociado perderá todas sus configuraciones y se reiniciará de fábrica. ¡Déjalo estar!"
        )
    if tipo == "Configuración (Tuberías)":
        return (
            "Esta carpeta (con un punto delante) es una 'Tubería' de configuración. Tus programas de "
            "programación (VSCode, Docker, Python) guardan aquí tus extensiones, contraseñas y "
            "preferencias. Moverla es como quitarle el cerebro al programa; dejará de funcionar y "
            "tendrás que volver a instalarlo todo."
        )
    return (
        "Este parece ser un archivo personal estándar (documento, foto, proyecto). "
        "No es vital para el sistema operativo y puedes organizarlo o borrarlo como quieras."
    )
