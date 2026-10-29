from pydantic import BaseModel


class ExportSummary(BaseModel):
    projects_exported: int
    files_written: int
    files_unchanged: int
    # Folders under Kairos/ whose project no longer exists; reported, never touched
    orphans: list[str]
