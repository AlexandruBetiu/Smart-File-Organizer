import json
import logging
import shutil
from collections import Counter
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from organizer.models import FilePlan, MoveRecord, OrganizationResult


class SmartFileOrganizer:
    TYPE_RULES = {
        "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"},
        "Documents": {".pdf", ".doc", ".docx", ".txt", ".rtf"},
        "Spreadsheets": {".xls", ".xlsx", ".csv"},
        "Presentations": {".ppt", ".pptx"},
        "Audio": {".mp3", ".wav", ".flac", ".aac"},
        "Videos": {".mp4", ".mov", ".avi", ".mkv"},
        "Archives": {".zip", ".rar", ".7z", ".tar", ".gz"},
        "Code": {".py", ".js", ".html", ".css", ".java", ".cpp", ".c", ".json"},
    }

    CRITERIA = {
        "type": "File type",
        "extension": "Exact extension",
        "date": "Modified month",
    }

    def __init__(self, history_path: str = "data/history.json", log_path: str = "logs/organizer.log"):
        self.history_path = Path(history_path)
        self.log_path = Path(log_path)
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._configure_logger()

    def _configure_logger(self) -> None:
        logger_name = f"smart_file_organizer.{self.log_path.resolve()}"
        self.logger = logging.getLogger(logger_name)
        if self.logger.handlers:
            return

        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        file_handler = logging.FileHandler(self.log_path, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def get_criteria(self) -> dict[str, str]:
        return dict(self.CRITERIA)

    def scan_folder(self, folder_path: str) -> list[Path]:
        folder = self._validate_folder(folder_path)
        return sorted([item for item in folder.iterdir() if item.is_file()], key=lambda item: item.name.lower())

    def preview_organization(self, folder_path: str, criterion: str = "type") -> list[FilePlan]:
        files = self.scan_folder(folder_path)
        self._validate_criterion(criterion)
        plans: list[FilePlan] = []

        for file_path in files:
            group_name = self._get_group_name(file_path, criterion)
            plans.append(
                FilePlan(
                    source=str(file_path),
                    file_name=file_path.name,
                    criterion=criterion,
                    group_name=group_name,
                    destination_folder=group_name,
                )
            )

        return plans

    def summarize_preview(self, folder_path: str, criterion: str = "type") -> dict[str, int]:
        preview = self.preview_organization(folder_path, criterion)
        counter = Counter(item.group_name for item in preview)
        return dict(sorted(counter.items(), key=lambda item: item[0].lower()))

    def organize_folder(
        self,
        folder_path: str,
        criterion: str = "type",
        progress_callback: Callable[[MoveRecord], None] | None = None,
        should_stop: Callable[[], bool] | None = None,
    ) -> OrganizationResult:
        folder = self._validate_folder(folder_path)
        self._validate_criterion(criterion)
        files = self.scan_folder(folder_path)
        result = OrganizationResult(folder=str(folder), criterion=criterion)
        run_time = datetime.now().isoformat(timespec="seconds")

        for file_path in files:
            if should_stop and should_stop():
                result.stopped = True
                self.logger.info("Organization stopped early for folder %s", folder)
                break

            group_name = self._get_group_name(file_path, criterion)
            destination_dir = folder / group_name
            destination_dir.mkdir(exist_ok=True)
            destination_file = self._build_available_path(destination_dir / file_path.name)

            try:
                shutil.move(str(file_path), str(destination_file))
                record = MoveRecord(
                    source=str(file_path),
                    destination=str(destination_file),
                    moved_at=run_time,
                    criterion=criterion,
                    group_name=group_name,
                )
                result.moved_files.append(record)
                self.logger.info(
                    "Moved | criterion=%s | source=%s | destination=%s | group=%s",
                    criterion,
                    file_path,
                    destination_file,
                    group_name,
                )
                if progress_callback:
                    progress_callback(record)
            except PermissionError as error:
                message = f"Permission error for {file_path.name}: {error}"
                result.errors.append(message)
                self.logger.error(message)
            except shutil.Error as error:
                message = f"Move error for {file_path.name}: {error}"
                result.errors.append(message)
                self.logger.error(message)

        if result.moved_files:
            self._save_run(folder, criterion, result.moved_files)

        return result

    def undo_last_run(self) -> list[MoveRecord]:
        history = self._load_history()
        if not history:
            return []

        last_run = history.pop()
        restored_files: list[MoveRecord] = []
        records = last_run.get("records", last_run)

        for item in reversed(records):
            source = Path(item["source"])
            destination = Path(item["destination"])
            restore_target = self._build_available_path(source)

            if not destination.exists():
                self.logger.warning("Skip undo, missing file: %s", destination)
                continue

            restore_target.parent.mkdir(parents=True, exist_ok=True)

            try:
                shutil.move(str(destination), str(restore_target))
                record = MoveRecord(
                    source=str(destination),
                    destination=str(restore_target),
                    moved_at=datetime.now().isoformat(timespec="seconds"),
                    criterion=item.get("criterion", "type"),
                    group_name=item.get("group_name", restore_target.parent.name),
                    status="restored",
                )
                restored_files.append(record)
                self.logger.info("Restored | source=%s | destination=%s", destination, restore_target)
            except PermissionError as error:
                self.logger.error("Permission error during undo for %s: %s", destination, error)
            except shutil.Error as error:
                self.logger.error("Undo move error for %s: %s", destination, error)

        self._write_history(history)
        return restored_files

    def _validate_folder(self, folder_path: str) -> Path:
        folder = Path(folder_path)
        if not folder.exists():
            raise FileNotFoundError(f"Folder not found: {folder}")
        if not folder.is_dir():
            raise NotADirectoryError(f"Path is not a folder: {folder}")
        return folder

    def _validate_criterion(self, criterion: str) -> None:
        if criterion not in self.CRITERIA:
            available = ", ".join(self.CRITERIA)
            raise ValueError(f"Invalid criterion '{criterion}'. Choose one of: {available}")

    def _get_group_name(self, file_path: Path, criterion: str) -> str:
        if criterion == "type":
            return self._get_type_group(file_path.suffix.lower())
        if criterion == "extension":
            return self._get_extension_group(file_path.suffix.lower())
        if criterion == "date":
            return self._get_date_group(file_path)
        raise ValueError(f"Unsupported criterion: {criterion}")

    def _get_type_group(self, extension: str) -> str:
        for category, extensions in self.TYPE_RULES.items():
            if extension in extensions:
                return category
        return "Others"

    def _get_extension_group(self, extension: str) -> str:
        if not extension:
            return "NO_EXTENSION"
        return extension.lstrip(".").upper()

    def _get_date_group(self, file_path: Path) -> str:
        modified_time = datetime.fromtimestamp(file_path.stat().st_mtime)
        return modified_time.strftime("%Y-%m")

    def _build_available_path(self, path: Path) -> Path:
        if not path.exists():
            return path

        counter = 1
        while True:
            candidate = path.with_name(f"{path.stem}_{counter}{path.suffix}")
            if not candidate.exists():
                return candidate
            counter += 1

    def _save_run(self, folder: Path, criterion: str, moved_files: list[MoveRecord]) -> None:
        history = self._load_history()
        history.append(
            {
                "folder": str(folder),
                "criterion": criterion,
                "run_at": datetime.now().isoformat(timespec="seconds"),
                "records": [item.to_dict() for item in moved_files],
            }
        )
        self._write_history(history)

    def _load_history(self) -> list[dict]:
        if not self.history_path.exists():
            return []

        with self.history_path.open("r", encoding="utf-8") as history_file:
            try:
                data = json.load(history_file)
            except json.JSONDecodeError:
                return []

        if not isinstance(data, list):
            return []
        return data

    def _write_history(self, history: list[dict]) -> None:
        with self.history_path.open("w", encoding="utf-8") as history_file:
            json.dump(history, history_file, indent=2)

    def close(self) -> None:
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)
