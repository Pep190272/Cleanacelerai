"""Tests for the risk evaluator (core business logic)."""
import pytest

from src.domain.models import RiskLevel
from src.domain.risk_evaluator import evaluate_file_risk, format_risk_label, get_risk_tag


class TestEvaluateFileRisk:
    """Tests for evaluate_file_risk()."""

    # ── System / Windows paths ─────────────────────────────────────────────
    def test_windows_folder_is_system(self) -> None:
        assert evaluate_file_risk(r"C:\Windows\System32\cmd.exe") == RiskLevel.SYSTEM

    def test_program_files_is_system(self) -> None:
        assert evaluate_file_risk(r"C:\Program Files\App\app.exe") == RiskLevel.SYSTEM

    def test_appdata_is_system(self) -> None:
        assert evaluate_file_risk(r"C:\Users\Josep\AppData\Local\Temp\foo.tmp") == RiskLevel.SYSTEM

    # ── Critical files ─────────────────────────────────────────────────────
    def test_pagefile_is_critical(self) -> None:
        assert evaluate_file_risk(r"C:\pagefile.sys") == RiskLevel.CRITICAL

    def test_dll_extension_is_critical(self) -> None:
        assert evaluate_file_risk(r"C:\Users\Josep\Downloads\some.dll") == RiskLevel.CRITICAL

    def test_ini_extension_is_critical(self) -> None:
        assert evaluate_file_risk(r"C:\Users\Josep\some_config.ini") == RiskLevel.CRITICAL

    def test_sys_extension_is_critical(self) -> None:
        assert evaluate_file_risk(r"C:\drivers\foo.sys") == RiskLevel.CRITICAL

    def test_ntuser_dat_is_critical(self) -> None:
        assert evaluate_file_risk(r"C:\Users\Josep\NTUSER.DAT") == RiskLevel.CRITICAL

    # ── Dotfiles ───────────────────────────────────────────────────────────
    def test_vscode_is_dotfile(self) -> None:
        assert evaluate_file_risk(r"C:\Users\Josep\.vscode\settings.json") == RiskLevel.DOTFILE

    def test_ssh_is_dotfile(self) -> None:
        assert evaluate_file_risk(r"C:\Users\Josep\.ssh\id_rsa") == RiskLevel.DOTFILE

    def test_git_is_dotfile(self) -> None:
        assert evaluate_file_risk(r"C:\Users\Josep\project\.git\config") == RiskLevel.DOTFILE

    def test_conda_is_dotfile(self) -> None:
        assert evaluate_file_risk(r"C:\Users\Josep\.conda\envs\base") == RiskLevel.DOTFILE

    # ── User keyword protection ────────────────────────────────────────────
    def test_custom_keyword_protection(self) -> None:
        result = evaluate_file_risk(
            r"C:\Users\Josep\myproject\src\main.py",
            protected_keywords=["myproject"],
        )
        assert result == RiskLevel.PROTECTED

    def test_keyword_not_present_returns_safe(self) -> None:
        result = evaluate_file_risk(
            r"C:\MyFolder\photo.jpg",
            protected_keywords=["myproject"],
        )
        assert result == RiskLevel.SAFE

    # ── Folder protection ──────────────────────────────────────────────────
    def test_protected_folder(self) -> None:
        result = evaluate_file_risk(
            r"C:\Users\Josep\Mis_Proyectos\app\main.py",
            protected_folders=[r"C:\Users\Josep\Mis_Proyectos"],
        )
        assert result == RiskLevel.PROJECT

    # ── Personal profile folders ───────────────────────────────────────────
    def test_downloads_is_personal(self) -> None:
        # "downloads" is in CARPETAS_PERFIL_PROTEGIDAS
        result = evaluate_file_risk(r"C:\Users\Josep\Downloads\photo.jpg")
        assert result == RiskLevel.PERSONAL

    def test_documents_is_personal(self) -> None:
        result = evaluate_file_risk(r"C:\Users\Josep\Documents\report.pdf")
        assert result == RiskLevel.PERSONAL

    # ── Safe files ─────────────────────────────────────────────────────────
    def test_random_file_is_safe(self) -> None:
        result = evaluate_file_risk(r"D:\SomeFolder\RandomFile.zip")
        assert result == RiskLevel.SAFE

    def test_empty_keywords_and_folders(self) -> None:
        result = evaluate_file_risk(
            r"D:\Work\project\app.py",
            protected_keywords=[],
            protected_folders=[],
        )
        assert result == RiskLevel.SAFE


class TestFormatRiskLabel:
    def test_safe_label(self) -> None:
        label = format_risk_label(RiskLevel.SAFE)
        assert "SEGURO" in label
        assert "🟢" in label

    def test_critical_label(self) -> None:
        label = format_risk_label(RiskLevel.CRITICAL)
        assert "CRÍTICO" in label
        assert "🔴" in label

    def test_dotfile_label_with_detail(self) -> None:
        label = format_risk_label(RiskLevel.DOTFILE, ".vscode")
        assert ".vscode" in label
        assert "🛡️" in label

    def test_system_label(self) -> None:
        label = format_risk_label(RiskLevel.SYSTEM)
        assert "Windows" in label

    def test_personal_label(self) -> None:
        label = format_risk_label(RiskLevel.PERSONAL)
        assert "PERSONAL" in label


class TestGetRiskTag:
    def test_safe_tag(self) -> None:
        assert get_risk_tag(RiskLevel.SAFE) == "seguro"

    def test_personal_tag(self) -> None:
        assert get_risk_tag(RiskLevel.PERSONAL) == "seguro"

    def test_critical_tag(self) -> None:
        assert get_risk_tag(RiskLevel.CRITICAL) == "critico"

    def test_system_tag(self) -> None:
        assert get_risk_tag(RiskLevel.SYSTEM) == "critico"

    def test_project_tag(self) -> None:
        assert get_risk_tag(RiskLevel.PROJECT) == "protegido"

    def test_dotfile_tag(self) -> None:
        assert get_risk_tag(RiskLevel.DOTFILE) == "dependencia"

    def test_protected_tag(self) -> None:
        assert get_risk_tag(RiskLevel.PROTECTED) == "dependencia"
