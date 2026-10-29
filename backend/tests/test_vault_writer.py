import os
import subprocess

import pytest

from app.exporters.vault import FileSystemVaultWriter
from app.services.errors import UnsafeVaultPath, VaultNotConfigured


@pytest.fixture
def vault(tmp_path):
    root = tmp_path / "vault"
    root.mkdir()
    return root


def symlink_or_skip(link, target):
    try:
        link.symlink_to(target, target_is_directory=True)
        return
    except (OSError, NotImplementedError):
        pass
    # Windows without symlink privilege: a directory junction redirects the same way
    if os.name == "nt":
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True)
        if result.returncode == 0:
            return
    pytest.skip("symlinks are not available here")


def test_writes_files_creating_kairos_and_project_folders(vault):
    writer = FileSystemVaultWriter(str(vault))

    assert writer.write("alpha/README.md", "hola ñandú\n") is True

    assert (vault / "Kairos" / "alpha" / "README.md").read_text(encoding="utf-8") == "hola ñandú\n"


def test_content_is_written_byte_for_byte_with_lf_endings(vault):
    FileSystemVaultWriter(str(vault)).write("a/x.md", "uno\ndos\n")

    assert (vault / "Kairos" / "a" / "x.md").read_bytes() == b"uno\ndos\n"


def test_unchanged_content_is_not_rewritten(vault):
    writer = FileSystemVaultWriter(str(vault))
    writer.write("a/x.md", "igual")
    path = vault / "Kairos" / "a" / "x.md"
    os.utime(path, (1_000_000, 1_000_000))

    assert writer.write("a/x.md", "igual") is False

    assert path.stat().st_mtime == 1_000_000


def test_changed_content_replaces_the_file(vault):
    writer = FileSystemVaultWriter(str(vault))
    writer.write("a/x.md", "uno")

    assert writer.write("a/x.md", "dos") is True

    assert (vault / "Kairos" / "a" / "x.md").read_text() == "dos"


def test_no_temporary_files_are_left_behind(vault):
    writer = FileSystemVaultWriter(str(vault))
    writer.write("a/x.md", "uno")
    writer.write("a/x.md", "dos")

    assert [p.name for p in (vault / "Kairos" / "a").iterdir()] == ["x.md"]


def test_failed_write_leaves_the_old_file_and_no_temp(vault, monkeypatch):
    writer = FileSystemVaultWriter(str(vault))
    writer.write("a/x.md", "viejo")

    def boom(*args):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        writer.write("a/x.md", "nuevo")

    assert [p.name for p in (vault / "Kairos" / "a").iterdir()] == ["x.md"]
    assert (vault / "Kairos" / "a" / "x.md").read_text() == "viejo"


@pytest.mark.parametrize("value", ["", "   "])
def test_empty_vault_path_is_not_configured(value):
    with pytest.raises(VaultNotConfigured):
        FileSystemVaultWriter(value)


def test_missing_vault_root_is_not_configured_and_not_created(tmp_path):
    missing = tmp_path / "nope"

    with pytest.raises(VaultNotConfigured):
        FileSystemVaultWriter(str(missing))

    assert not missing.exists()


def test_vault_path_that_is_a_file_is_not_configured(tmp_path):
    file = tmp_path / "file"
    file.write_text("x")

    with pytest.raises(VaultNotConfigured):
        FileSystemVaultWriter(str(file))


@pytest.mark.parametrize(
    "path",
    [
        "../escape.md",
        "a/../../escape.md",
        "a/../..",
        "/etc/passwd",
        "..",
        ".",
        "",
        "a\\..\\..\\escape.md",
        "C:\\escape.md",
    ],
)
def test_paths_that_leave_kairos_are_rejected(vault, path):
    writer = FileSystemVaultWriter(str(vault))

    with pytest.raises(UnsafeVaultPath):
        writer.write(path, "x")

    assert not (vault.parent / "escape.md").exists()
    assert not (vault / "escape.md").exists()


def test_symlinked_project_folder_leaving_the_vault_is_rejected(vault, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (vault / "Kairos").mkdir()
    symlink_or_skip(vault / "Kairos" / "evil", outside)
    writer = FileSystemVaultWriter(str(vault))

    with pytest.raises(UnsafeVaultPath):
        writer.write("evil/README.md", "x")

    assert list(outside.iterdir()) == []


def test_symlinked_kairos_folder_leaving_the_vault_is_rejected(vault, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    symlink_or_skip(vault / "Kairos", outside)
    writer = FileSystemVaultWriter(str(vault))

    with pytest.raises(UnsafeVaultPath):
        writer.write("a/README.md", "x")
    with pytest.raises(UnsafeVaultPath):
        writer.list_folders()

    assert list(outside.iterdir()) == []


def test_symlinked_file_leaving_the_vault_is_rejected(vault, tmp_path):
    outside = tmp_path / "secret.md"
    outside.write_text("original")
    (vault / "Kairos" / "a").mkdir(parents=True)
    try:
        (vault / "Kairos" / "a" / "README.md").symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available here")
    writer = FileSystemVaultWriter(str(vault))

    with pytest.raises(UnsafeVaultPath):
        writer.write("a/README.md", "x")

    assert outside.read_text() == "original"


def test_list_folders_returns_only_directories(vault):
    writer = FileSystemVaultWriter(str(vault))
    assert writer.list_folders() == []
    writer.write("b/README.md", "x")
    writer.write("a/README.md", "x")
    writer.write("_bandeja.md", "x")

    assert writer.list_folders() == ["a", "b"]
