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
        # settings.json is a code file → now returns CRITICAL (Patch 2)
        # Use a non-code extension to test the dotfile path logic
        assert evaluate_file_risk(r"C:\Users\Josep\.vscode\settings.bin") == RiskLevel.DOTFILE

    def test_ssh_is_dotfile(self) -> None:
        assert evaluate_file_risk(r"C:\Users\Josep\.ssh\id_rsa") == RiskLevel.DOTFILE

    def test_git_is_dotfile(self) -> None:
        assert evaluate_file_risk(r"C:\Users\Josep\project\.git\config") == RiskLevel.DOTFILE

    def test_conda_is_dotfile(self) -> None:
        assert evaluate_file_risk(r"C:\Users\Josep\.conda\envs\base") == RiskLevel.DOTFILE

    # ── User keyword protection ────────────────────────────────────────────
    def test_custom_keyword_protection(self) -> None:
        # .py files now return CRITICAL (Patch 2). Use a non-code extension
        # to isolate keyword-protection logic.
        result = evaluate_file_risk(
            r"C:\Users\Josep\myproject\src\data.bin",
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
        # .py files now return CRITICAL (Patch 2). Use a non-code extension
        # to isolate protected-folder logic.
        result = evaluate_file_risk(
            r"C:\Users\Josep\Mis_Proyectos\app\build.zip",
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
        # .py files now return CRITICAL (Patch 2). Use a non-code extension
        # to test the "nothing special → SAFE" base case.
        result = evaluate_file_risk(
            r"D:\Work\project\data.bin",
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


class TestCodeExtensionProtection:
    """Patch 2: web/code extensions must ALWAYS return CRITICAL tier."""

    @pytest.mark.parametrize("ext", [
        ".php", ".css", ".html", ".htm", ".js", ".mjs", ".ts", ".tsx", ".jsx",
        ".py", ".rb", ".go", ".rs", ".java", ".kt", ".swift", ".c", ".h", ".cpp",
        ".json", ".yaml", ".yml", ".toml", ".xml", ".md", ".mdx", ".sql",
        ".sh", ".bash", ".ps1", ".bat", ".cmd",
    ])
    def test_code_extension_is_critical(self, ext: str) -> None:
        result = evaluate_file_risk(rf"D:\SomeFolder\file{ext}")
        assert result == RiskLevel.CRITICAL, (
            f"Extension {ext!r} should return CRITICAL but got {result}"
        )

    def test_php_file_in_downloads_is_critical_not_personal(self) -> None:
        """PERSONAL tier must NOT win over CRITICAL for code extensions."""
        result = evaluate_file_risk(r"C:\Users\Josep\Downloads\style.css")
        assert result == RiskLevel.CRITICAL

    def test_py_file_with_no_special_path_is_critical(self) -> None:
        result = evaluate_file_risk(r"D:\random\script.py")
        assert result == RiskLevel.CRITICAL

    def test_ts_file_is_critical(self) -> None:
        result = evaluate_file_risk(r"D:\projects\src\app.ts")
        assert result == RiskLevel.CRITICAL

    def test_jpg_is_still_safe(self) -> None:
        """Image files should NOT be blocked by the code extension guard."""
        result = evaluate_file_risk(r"D:\Photos\vacation.jpg")
        assert result == RiskLevel.SAFE

    def test_zip_is_still_safe(self) -> None:
        result = evaluate_file_risk(r"D:\Archive\backup.zip")
        assert result == RiskLevel.SAFE

    def test_env_file_is_critical(self) -> None:
        result = evaluate_file_risk(r"D:\project\.env")
        assert result == RiskLevel.CRITICAL

    def test_gitignore_is_critical(self) -> None:
        result = evaluate_file_risk(r"D:\project\.gitignore")
        assert result == RiskLevel.CRITICAL


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
