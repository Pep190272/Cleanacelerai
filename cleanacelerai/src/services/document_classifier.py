"""Document classification service using keyword heuristics and PDF text extraction."""
from __future__ import annotations

import os
from collections import Counter
from typing import Callable

import fitz  # PyMuPDF

from cleanacelerai.src.domain.constants import DOCUMENT_EXTENSIONS, DOC_KEYWORDS
from cleanacelerai.src.domain.models import (
    DocumentCategory,
    DocumentClassification,
    DocumentAnalysisResult,
)


def classify_documents(
    folder: str, progress_cb: Callable[[int], None] | None = None
) -> DocumentAnalysisResult:
    """Scan a folder and classify all PDF documents by content.

    Args:
        folder: Absolute path to the folder to scan.
        progress_cb: Optional callback receiving progress percentage (0-100).

    Returns:
        DocumentAnalysisResult with classifications and summary.
    """
    doc_files = _find_documents(folder)
    total = len(doc_files)
    classifications: list[DocumentClassification] = []
    unreadable: list[str] = []

    for i, doc_path in enumerate(doc_files):
        try:
            text, page_count = _extract_text(doc_path)
            if not text.strip():
                unreadable.append(doc_path)
                continue

            category, confidence = _classify_text(text)
            preview = text[:200].strip()
            suggested = _suggest_folder(category)

            classifications.append(
                DocumentClassification(
                    path=doc_path,
                    name=os.path.basename(doc_path),
                    category=category,
                    confidence=confidence,
                    suggested_folder=suggested,
                    page_count=page_count,
                    extract_preview=preview,
                )
            )
        except Exception:
            unreadable.append(doc_path)

        if progress_cb and total > 0:
            progress_cb(int((i + 1) / total * 100))

    category_summary = Counter(c.category for c in classifications)

    return DocumentAnalysisResult(
        classifications=classifications,
        category_summary=dict(category_summary),
        total_documents=total,
        unreadable=unreadable,
    )


def _find_documents(folder: str) -> list[str]:
    """Find all document files in a folder (non-recursive).

    Args:
        folder: Absolute path to the folder.

    Returns:
        Sorted list of absolute paths to document files.
    """
    results = []
    try:
        for entry in os.scandir(folder):
            if entry.is_file() and entry.name.lower().endswith(DOCUMENT_EXTENSIONS):
                results.append(entry.path)
    except PermissionError:
        pass
    return sorted(results)


def _extract_text(pdf_path: str, max_pages: int = 5) -> tuple[str, int]:
    """Extract text from a PDF using PyMuPDF.

    Args:
        pdf_path: Absolute path to the PDF file.
        max_pages: Maximum number of pages to read for classification.

    Returns:
        Tuple of (extracted_text, total_page_count).
    """
    doc = fitz.open(pdf_path)
    page_count = len(doc)
    pages_to_read = min(page_count, max_pages)
    text_parts = []
    for i in range(pages_to_read):
        text_parts.append(doc[i].get_text())
    doc.close()
    return "\n".join(text_parts), page_count


def _classify_text(text: str) -> tuple[DocumentCategory, float]:
    """Classify document text using keyword matching heuristics.

    Args:
        text: Extracted text content from the document.

    Returns:
        Tuple of (category, confidence_score).
    """
    text_lower = text.lower()
    scores: dict[str, float] = {}

    for category_name, keywords in DOC_KEYWORDS.items():
        score = 0.0
        for keyword in keywords:
            count = text_lower.count(keyword)
            if count > 0:
                # Weight by keyword length (longer = more specific = higher weight)
                weight = len(keyword.split())
                score += count * weight
        scores[category_name] = score

    if not scores or max(scores.values()) == 0:
        return DocumentCategory.UNKNOWN, 0.0

    best_category = max(scores, key=scores.get)  # type: ignore[arg-type]
    best_score = scores[best_category]
    total_score = sum(scores.values())

    confidence = min(best_score / total_score, 1.0) if total_score > 0 else 0.0

    # Boost confidence if score is high enough
    if best_score >= 10:
        confidence = min(confidence + 0.1, 1.0)

    return DocumentCategory[best_category], confidence


def _suggest_folder(category: DocumentCategory) -> str:
    """Suggest a folder name for a document category.

    Args:
        category: The document category.

    Returns:
        Spanish folder name suggestion.
    """
    folder_map = {
        DocumentCategory.INVOICE: "Facturas",
        DocumentCategory.RECEIPT: "Recibos",
        DocumentCategory.CONTRACT: "Contratos",
        DocumentCategory.TUTORIAL: "Tutoriales",
        DocumentCategory.BOOK: "Libros",
        DocumentCategory.MANUAL: "Manuales",
        DocumentCategory.LETTER: "Cartas",
        DocumentCategory.REPORT: "Informes",
        DocumentCategory.ACADEMIC: "Académicos",
        DocumentCategory.UNKNOWN: "Sin Clasificar",
    }
    return folder_map.get(category, "Sin Clasificar")
