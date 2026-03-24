"""Domain layer: models, constants, and core business logic."""
from .constants import (
    ARCHIVOS_PROHIBIDOS,
    CARPETAS_PERFIL_PROTEGIDAS,
    CARPETAS_SISTEMA,
    COLOR_ACCENT,
    COLOR_BG,
    COLOR_BORDER,
    COLOR_CARD,
    COLOR_DANGER,
    COLOR_SUCCESS,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_MUTED,
    COLOR_WARNING,
    DOTFILES_CRITICOS,
    EXTENSIONES_SISTEMA,
)
from .models import CleanupResult, DuplicateGroup, FileInfo, RiskLevel
from .risk_evaluator import evaluate_file_risk, format_risk_label, get_risk_tag

__all__ = [
    "CleanupResult",
    "DuplicateGroup",
    "FileInfo",
    "RiskLevel",
    "evaluate_file_risk",
    "format_risk_label",
    "get_risk_tag",
    "CARPETAS_SISTEMA",
    "CARPETAS_PERFIL_PROTEGIDAS",
    "DOTFILES_CRITICOS",
    "EXTENSIONES_SISTEMA",
    "ARCHIVOS_PROHIBIDOS",
    "COLOR_BG",
    "COLOR_CARD",
    "COLOR_BORDER",
    "COLOR_TEXT_MAIN",
    "COLOR_TEXT_MUTED",
    "COLOR_ACCENT",
    "COLOR_SUCCESS",
    "COLOR_WARNING",
    "COLOR_DANGER",
]
