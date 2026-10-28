from datetime import datetime
from pathlib import Path
from desknest.storage.database import Database

class BackupService:
    def __init__(self, database: Database):
        self.database = database
        self.directory = database.path.parent / "backups"

    def create_backup(self):
        name = datetime.now().strftime("desknest-%Y%m%d-%H%M%S-%f.db")
        return self.database.backup_to(self.directory / name)

    def list_backups(self):
        return sorted(self.directory.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True)

    def restore(self, source):
        self.database.restore_from(source)
