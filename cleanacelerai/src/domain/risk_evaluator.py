"""Core business logic: risk evaluation for files and folders."""
from __future__ import annotations

import os

from .constants import (
    ARCHIVOS_PROHIBIDOS,
    CARPETAS_PERFIL_PROTEGIDAS,
    CARPETAS_SISTEMA,
    DOTFILES_CRITICOS,
    EXTENSIONES_SISTEMA,
)
from .models import RiskLevel
from .utils import normalizar_ruta


def evaluate_file_risk(
    path: str,
    protected_keywords: list[str] | None = None,
    protected_folders: list[str] | None = None,
) -> RiskLevel:
    """
    Evaluate the risk level of a file or folder.

    Args:
        path: Absolute path to evaluate.
        protected_keywords: User-defined keywords (dotfiles, etc.) to protect.
        protected_folders: User-defined folder paths to protect.

    Returns:
        A RiskLevel enum value.
    """
    if protected_keywords is None:
        protected_keywords = []
    if protected_folders is None:
        protected_folders = []

    ruta_lower = path.lower()
    partes_ruta = normalizar_ruta(path)
    nombre_archivo = os.path.basename(ruta_lower)

    # 1. Windows system protection — absolute block
    if CARPETAS_SISTEMA.intersection(partes_ruta):
        return RiskLevel.SYSTEM

    if nombre_archivo in ARCHIVOS_PROHIBIDOS:
        return RiskLevel.CRITICAL

    if nombre_archivo.endswith(EXTENSIONES_SISTEMA):
        return RiskLevel.CRITICAL

    # 2. Dotfile protection (tuberías de configuración)
    for parte in partes_ruta:
        if parte in DOTFILES_CRITICOS:
            return RiskLevel.DOTFILE

    # 3. User-defined keyword protection
    for kw in protected_keywords:
        if kw.lower() in ruta_lower:
            return RiskLevel.PROTECTED

    # 4. User-defined folder protection
    ruta_norm = os.path.normpath(path).lower()
    for folder in protected_folders:
        if os.path.normpath(folder).lower() in ruta_norm:
            return RiskLevel.PROJECT

    # 5. User profile folders (safe to move, not safe to delete)
    for perfil in CARPETAS_PERFIL_PROTEGIDAS:
        if perfil in partes_ruta:
            return RiskLevel.PERSONAL

    return RiskLevel.SAFE


def format_risk_label(risk: RiskLevel, detail: str = "") -> str:
    """
    Return a human-readable label for a risk level.

    Args:
        risk: The RiskLevel to format.
        detail: Optional detail string (e.g. matched keyword).

    Returns:
        Formatted Spanish label with emoji prefix.
    """
    labels: dict[RiskLevel, str] = {
        RiskLevel.SAFE: "🟢 SEGURO (Borrable)",
        RiskLevel.PERSONAL: "🟢 PERSONAL (Seguro de Mover)",
        RiskLevel.PROJECT: "🟡 PROYECTO",
        RiskLevel.PROTECTED: f"🛡️ PROTEGIDO ({detail})" if detail else "🛡️ PROTEGIDO",
        RiskLevel.DOTFILE: f"🛡️ DOTFILE ({detail})" if detail else "🛡️ DOTFILE",
        RiskLevel.CRITICAL: "🔴 CRÍTICO (Sistema)",
        RiskLevel.SYSTEM: "🔴 CRÍTICO (Windows)",
    }
    return labels[risk]


def get_risk_tag(risk: RiskLevel) -> str:
    """Map a RiskLevel to a Treeview tag name."""
    mapping: dict[RiskLevel, str] = {
        RiskLevel.SAFE: "seguro",
        RiskLevel.PERSONAL: "seguro",
        RiskLevel.PROJECT: "protegido",
        RiskLevel.PROTECTED: "dependencia",
        RiskLevel.DOTFILE: "dependencia",
        RiskLevel.CRITICAL: "critico",
        RiskLevel.SYSTEM: "critico",
    }
    return mapping[risk]
