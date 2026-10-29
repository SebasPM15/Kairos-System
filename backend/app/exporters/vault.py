"""Where the export lands: a narrow writer interface and its filesystem implementation."""

import os
import tempfile
from pathlib import Path, PurePosixPath
from typing import Protocol

from app.services.errors import UnsafeVaultPath, VaultNotConfigured

# Everything Kairos writes lives under this folder of the vault
EXPORT_DIR = "Kairos"


class VaultWriter(Protocol):
    """Paths are relative to the Kairos/ folder and use forward slashes."""

    def write(self, relative_path: str, content: str) -> bool:
        """Store the file; return False when it already had exactly this content."""
        ...

    def list_folders(self) -> list[str]:
        """Names of the folders directly under Kairos/."""
        ...


class FileSystemVaultWriter:
    def __init__(self, vault_path: str) -> None:
        if not vault_path.strip():
            raise VaultNotConfigured()
        root = Path(vault_path).expanduser()
        # The vault itself is the user's: never create it, only Kairos/ inside it
        if not root.is_dir():
            raise VaultNotConfigured()
        self._root = root.resolve()
        self._base = self._root / EXPORT_DIR

    def write(self, relative_path: str, content: str) -> bool:
        target = self._resolve(relative_path)
        data = content.encode("utf-8")
        if target.is_file() and target.read_bytes() == data:
            return False
        target.parent.mkdir(parents=True, exist_ok=True)
        # Same directory so the final replace is atomic
        descriptor, temp_name = tempfile.mkstemp(dir=target.parent, prefix=".kairos-", suffix=".tmp")
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(data)
            # mkstemp creates 0600; the vault is read by other users (Obsidian on the host)
            os.chmod(temp_name, 0o644)
            os.replace(temp_name, target)
        except BaseException:
            Path(temp_name).unlink(missing_ok=True)
            raise
        return True

    def list_folders(self) -> list[str]:
        base = self._checked_base()
        if not base.is_dir():
            return []
        return sorted(entry.name for entry in base.iterdir() if entry.is_dir())

    def _checked_base(self) -> Path:
        base = self._base.resolve()
        if not base.is_relative_to(self._root):
            raise UnsafeVaultPath(EXPORT_DIR)
        return base

    def _resolve(self, relative_path: str) -> Path:
        pure = PurePosixPath(relative_path)
        if "\\" in relative_path or pure.is_absolute() or any(part in ("", ".", "..") for part in pure.parts):
            raise UnsafeVaultPath(relative_path)
        if not pure.parts:
            raise UnsafeVaultPath(relative_path)
        base = self._checked_base()
        # resolve() follows symlinks, so a link leading out of Kairos/ ends up outside it
        target = (base / pure).resolve()
        if target == base or not target.is_relative_to(base):
            raise UnsafeVaultPath(relative_path)
        return target
