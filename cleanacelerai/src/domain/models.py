"""Domain models for Cleanacelerai."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class RiskLevel(Enum):
    """Risk classification for files and folders."""
    SAFE = "SAFE"           # Borrable con seguridad
    PERSONAL = "PERSONAL"   # Archivo personal del usuario (seguro de mover)
    PROJECT = "PROJECT"     # Proyecto protegido por el usuario
    PROTECTED = "PROTECTED" # Protegido por palabra clave del usuario
    DOTFILE = "DOTFILE"     # Dotfile crítico (.vscode, .ssh, etc.)
    CRITICAL = "CRITICAL"   # Sistema operativo (DLLs, SYS, etc.)
    SYSTEM = "SYSTEM"       # Carpeta de sistema Windows


@dataclass
class FileInfo:
    """Represents a file with its metadata."""
    path: str
    size: int
    mtime: float
    hash: Optional[str] = None

    @property
    def size_mb(self) -> float:
        return self.size / (1024 * 1024)

    @property
    def name(self) -> str:
        return os.path.basename(self.path)

    @property
    def extension(self) -> str:
        return os.path.splitext(self.path)[1].lower()


@dataclass
class DuplicateGroup:
    """A group of files that are identical (same hash)."""
    hash: str
    files: list[FileInfo] = field(default_factory=list)

    @property
    def size_mb(self) -> float:
        return self.files[0].size_mb if self.files else 0.0

    @property
    def recoverable_mb(self) -> float:
        """Space that could be freed by keeping one copy."""
        if len(self.files) < 2:
            return 0.0
        return self.files[0].size_mb * (len(self.files) - 1)


@dataclass
class CleanupResult:
    """Result of a cleanup operation."""
    deleted: int = 0
    freed_mb: float = 0.0
    errors: list[str] = field(default_factory=list)

    @property
    def freed_gb(self) -> float:
        return self.freed_mb / 1024

    def add_error(self, path: str, reason: str) -> None:
        self.errors.append(f"{path}: {reason}")


# --- Intelligent Chaos Advisor (Phase 1: Document Classification) ---

class DocumentCategory(Enum):
    """Category classification for PDF documents."""
    INVOICE = "FACTURA"
    RECEIPT = "RECIBO"
    CONTRACT = "CONTRATO"
    TUTORIAL = "TUTORIAL"
    BOOK = "LIBRO"
    MANUAL = "MANUAL"
    LETTER = "CARTA"
    REPORT = "INFORME"
    ACADEMIC = "ACADÉMICO"
    UNKNOWN = "DESCONOCIDO"


@dataclass
class DocumentClassification:
    """Classification result for a single document."""
    path: str
    name: str
    category: DocumentCategory
    confidence: float  # 0.0 - 1.0
    suggested_folder: str
    page_count: int
    extract_preview: str  # First ~200 chars


@dataclass
class DocumentAnalysisResult:
    """Aggregated result of classifying all documents in a folder."""
    classifications: list[DocumentClassification]
    category_summary: dict[DocumentCategory, int]
    total_documents: int
    unreadable: list[str]


# --- Intelligent Chaos Advisor (Phase 2: Face Recognition) ---

@dataclass
class FaceCluster:
    """A cluster of images containing the same face."""
    cluster_id: int
    suggested_name: str | None
    image_paths: list[str]
    representative_path: str


@dataclass
class FaceAnalysisResult:
    """Aggregated result of face clustering across images."""
    clusters: list[FaceCluster]
    unmatched_images: list[str]
    total_images: int
    total_faces: int


# --- Deep Cleaner (Limpieza Profunda) ---

class DeepCleanRisk(Enum):
    """Risk classification for deep-clean scanner."""
    SYSTEM = "SISTEMA"
    CRITICAL = "CRITICO"
    ACTIVE = "ACTIVO"
    CACHE = "CACHE"
    EMPTY = "VACIO"


class DeepCleanBundle(Enum):
    """Logical grouping for deep-clean entries."""
    AI_TOOLS = "Herramientas de IA"
    EDITORS_DEV = "Editores y Desarrollo"
    CACHE_TEMP = "Cache y Temporales"
    WINDOWS_SYSTEM = "Sistema Windows"
    UNKNOWN = "Desconocido"


@dataclass
class DeepCleanEntry:
    """A single folder found by the deep scanner."""
    path: str
    name: str
    size_bytes: int | None
    risk: DeepCleanRisk
    bundle: DeepCleanBundle
    description: str
    creator: str
    last_modified: float | None
    is_in_use: bool
    special_note: str | None
    delete_instructions: str | None


@dataclass
class DeepCleanResult:
    """Aggregated result of the deep scan."""
    entries: list[DeepCleanEntry]
    total_scanned: int
    total_recoverable_bytes: int
    scan_errors: list[str]
