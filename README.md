<div align="center">

# Cleanacelerai PRO

### Windows Desktop Utility for Intelligent File Management & Cleanup

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![CustomTkinter](https://img.shields.io/badge/CustomTkinter-UI-1F6FEB?style=for-the-badge)](https://github.com/TomSchimansky/CustomTkinter)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows_10%2F11-0078D6?style=for-the-badge&logo=windows&logoColor=white)](https://www.microsoft.com/windows)

---

<a href="#-features">Features</a> &nbsp;&bull;&nbsp;
<a href="#-quick-start">Quick Start</a> &nbsp;&bull;&nbsp;
<a href="#-architecture">Architecture</a> &nbsp;&bull;&nbsp;
<a href="#-development">Development</a> &nbsp;&bull;&nbsp;
<a href="#-roadmap">Roadmap</a>

---

**Language / Idioma / Llengua**

[<img src="https://raw.githubusercontent.com/lipis/flag-icons/main/flags/4x3/gb.svg" width="24" alt="English"> English](#overview) &nbsp;&nbsp;
[<img src="https://raw.githubusercontent.com/lipis/flag-icons/main/flags/4x3/es.svg" width="24" alt="Español"> Español](#-seccion-en-espanol) &nbsp;&nbsp;
[<img src="https://raw.githubusercontent.com/lipis/flag-icons/main/flags/4x3/es-ct.svg" width="24" alt="Català"> Català](#-seccio-en-catala)

</div>

---

## Overview

Cleanacelerai PRO is a desktop application that helps you keep your Windows system clean and organized. It combines **AI-powered file classification**, **browser bookmark management**, **deep system scanning**, **duplicate detection**, and **junk cleanup** into a single dark-themed dashboard.

Built with **Clean/Hexagonal Architecture** and the **MVP pattern**, the codebase is modular, testable, and ready for feature expansion.

---

## Features

### Intelligent Chaos Advisor

The AI Advisor has three specialized tabs:

| Tab | Description |
|-----|-------------|
| **Orden General** | Analyzes any folder and classifies files by type, risk level, and suggested action (move, delete, protect) |
| **Documentos PDF** | Extracts text from PDFs using PyMuPDF and classifies them into 10 categories: invoices, books, tutorials, contracts, reports, and more |
| **Limpieza Profunda** | Scans system dotfiles and config folders with a knowledge base of 45+ known folders. Shows risk level, description, and clear recommendations for each |

### Browser Bookmark Manager

| Feature | Description |
|---------|-------------|
| **Auto-detection** | Finds Chrome, Edge, and Brave with profile names and emails |
| **4-tier categorization** | Domain rules, content keywords, URL structure analysis, and live web page fetching |
| **12 categories** | Productividad, Desarrollo, IA, Herramientas, Entretenimiento, Redes Sociales, and more |
| **Subcategories** | IA/Chatbots, IA/Modelos, Desarrollo/Repos, Desarrollo/Documentacion |
| **Name cleaning** | Removes clutter like "- YouTube", "| Medium", chatbot prefixes. Max 40 chars |
| **Dead link detection** | Marks 404/unreachable URLs for cleanup |
| **Folder organization** | Rebuilds the bookmark bar with clean category folders directly in the browser file |
| **Persistent cache** | Deep categorization results survive across sessions |

### Core Tools

| Tool | Description |
|------|-------------|
| **Duplicate Finder** | Content-based deduplication using SHA-256 hashing. Size-first strategy for speed |
| **Temp Cleaner** | Scans `%TEMP%`, `%TMP%`, and Windows temp folders. Safe deletion with permission handling |
| **Bulk Renamer** | Sequential date-based renaming with pattern support |
| **Protection Rules** | Multi-layer risk engine: system folders, dotfiles, user keywords, custom paths |
| **Dashboard** | Real-time KPIs: recovered space, duplicate count, junk count, activity log |

---

## Quick Start

### Prerequisites

- **Windows 10/11** (64-bit)
- **Python 3.10+** installed

### Installation

```bash
# Clone the repository
git clone https://github.com/Pep190272/Cleanacelerai.git
cd Cleanacelerai

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Run

```bash
python -m cleanacelerai.run
```

### Build Executable

```bash
pip install pyinstaller
pyinstaller cleanacelerai.spec
# Output: dist/cleanacelerai.exe
```

---

## Architecture

The project follows **Hexagonal (Clean) Architecture** with the **MVP** (Model-View-Presenter) pattern:

```
cleanacelerai/
  src/
    domain/          # Enums, dataclasses, constants, risk evaluator (pure logic, no I/O)
    services/        # Stateless business logic (scanning, classifying, organizing)
    infrastructure/  # OS operations (file system, config persistence, model cache)
    ui/
      views/         # Passive CustomTkinter widgets (zero business logic)
      presenters/    # Coordinate services with views, manage threading
```

### Key Design Decisions

- **Threading**: All heavy operations (scanning, hashing, web fetching) run in daemon threads. UI updates via `view.after(0, callback)` for thread safety
- **Stateless services**: Services are pure functions with optional progress callbacks. No shared state
- **Risk engine**: Multi-layer protection prevents accidental deletion of system files, dotfiles, and user-defined paths
- **Bookmark rebuild**: Instead of editing bookmarks by ID (fragile with Chrome Sync), the organizer extracts all URLs, categorizes them, and rebuilds the bookmark bar from scratch

---

## Development

### Project Structure

```
cleanacelerai/
  __init__.py              # Version: 25.0.0
  run.py                   # Entry point
  src/
    main.py                # App initialization
    domain/
      models.py            # FileInfo, DuplicateGroup, DocumentCategory, DeepCleanRisk, ...
      constants.py         # Colors, system folders, keywords, risk mappings
      risk_evaluator.py    # Multi-layer file risk classification
    services/
      bookmark_manager.py  # 4-tier categorization, name cleaning, organize, dead links
      chaos_advisor.py     # Folder analysis with heuristics
      deep_scanner.py      # System folder scanner with knowledge base
      document_classifier.py  # PDF text extraction + keyword classification
      duplicate_finder.py  # SHA-256 content deduplication
      temp_cleaner.py      # Windows temp folder scanning
      file_renamer.py      # Batch renaming
    infrastructure/
      config_service.py    # JSON config in ~/.cleanacelerai/
      file_system.py       # Safe deletion (handles read-only, long paths)
      model_manager.py     # Model cache on D: drive
    ui/
      main_window.py       # Top-level orchestrator
      views/               # 7 passive views (dashboard, duplicates, advisor, ...)
      presenters/          # 6 presenters with threading
  tests/                   # pytest unit tests
```

### Running Tests

```bash
cd cleanacelerai
python -m pytest tests/ -v
```

### Configuration

User settings are stored in `%USERPROFILE%\.cleanacelerai\config.json` (auto-created on first run).

Deep categorization cache is stored in `%USERPROFILE%\.cleanacelerai\deep_cache.json`.

---

## Roadmap

- [x] AI Chaos Advisor with tabbed interface
- [x] PDF document classifier (keyword heuristics)
- [x] Deep system cleaner with knowledge base
- [x] Bookmark manager with 4-tier categorization
- [x] Dead link detection
- [ ] Face recognition in images (OpenCV YuNet + SFace)
- [ ] TF-IDF + scikit-learn for improved document classification
- [ ] Drag-and-drop support
- [ ] Export cleanup reports

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| UI Framework | CustomTkinter 5.x |
| PDF Engine | PyMuPDF (fitz) |
| Architecture | Hexagonal / Clean + MVP |
| Testing | pytest |
| Packaging | PyInstaller |

---

## Credits

- Application icon from [icon-icons.com](https://icon-icons.com)
- Built with [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) by Tom Schimansky

---

<div align="center">

**Cleanacelerai PRO** &mdash; Keep your system clean and organized.

</div>

---

## <img src="https://raw.githubusercontent.com/lipis/flag-icons/main/flags/4x3/es.svg" width="24" alt="ES"> Seccion en Espanol

### Asesor de Caos Inteligente

El Asesor de IA tiene tres pestanas especializadas:

| Pestana | Descripcion |
|---------|-------------|
| **Orden General** | Analiza cualquier carpeta y clasifica archivos por tipo, nivel de riesgo y accion sugerida |
| **Documentos PDF** | Extrae texto de PDFs con PyMuPDF y los clasifica en 10 categorias: facturas, libros, tutoriales, contratos, informes, y mas |
| **Limpieza Profunda** | Escanea dotfiles y carpetas del sistema con una base de conocimiento de 45+ carpetas conocidas. Muestra nivel de riesgo, descripcion y recomendaciones claras |

### Gestor de Marcadores del Navegador

| Funcion | Descripcion |
|---------|-------------|
| **Auto-deteccion** | Encuentra Chrome, Edge y Brave con nombres de perfil y emails |
| **Categorizacion en 4 niveles** | Reglas de dominio, keywords de contenido, analisis de estructura de URL, y busqueda en paginas web |
| **12 categorias** | Productividad, Desarrollo, IA, Herramientas, Entretenimiento, Redes Sociales, y mas |
| **Limpieza de nombres** | Elimina basura como "- YouTube", "| Medium", prefijos de chatbots. Maximo 40 caracteres |
| **Deteccion de enlaces muertos** | Marca URLs 404/inaccesibles para limpieza |
| **Organizacion en carpetas** | Reconstruye la barra de marcadores con carpetas por categoria directamente en el archivo del navegador |

### Inicio Rapido

```bash
git clone https://github.com/Pep190272/Cleanacelerai.git
cd Cleanacelerai
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m cleanacelerai.run
```

---

## <img src="https://raw.githubusercontent.com/lipis/flag-icons/main/flags/4x3/es-ct.svg" width="24" alt="CA"> Seccio en Catala

### Assessor de Caos Intel-ligent

L'Assessor d'IA te tres pestanyes especialitzades:

| Pestanya | Descripcio |
|----------|------------|
| **Ordre General** | Analitza qualsevol carpeta i classifica arxius per tipus, nivell de risc i accio suggerida |
| **Documents PDF** | Extreu text de PDFs amb PyMuPDF i els classifica en 10 categories: factures, llibres, tutorials, contractes, informes, i mes |
| **Neteja Profunda** | Escaneja dotfiles i carpetes del sistema amb una base de coneixement de 45+ carpetes conegudes. Mostra nivell de risc, descripcio i recomanacions clares |

### Gestor de Marcadors del Navegador

| Funcio | Descripcio |
|--------|------------|
| **Auto-deteccio** | Troba Chrome, Edge i Brave amb noms de perfil i emails |
| **Categoritzacio en 4 nivells** | Regles de domini, keywords de contingut, analisi d'estructura d'URL, i cerca a pagines web |
| **12 categories** | Productivitat, Desenvolupament, IA, Eines, Entreteniment, Xarxes Socials, i mes |
| **Neteja de noms** | Elimina brossa com "- YouTube", "| Medium", prefixos de chatbots. Maxim 40 caracters |
| **Deteccio d'enllacos morts** | Marca URLs 404/inaccessibles per a neteja |
| **Organitzacio en carpetes** | Reconstrueix la barra de marcadors amb carpetes per categoria directament a l'arxiu del navegador |

### Inici Rapid

```bash
git clone https://github.com/Pep190272/Cleanacelerai.git
cd Cleanacelerai
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m cleanacelerai.run
```
