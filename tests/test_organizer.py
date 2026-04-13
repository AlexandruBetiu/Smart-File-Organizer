import tempfile
import unittest
from pathlib import Path

from organizer.organizer import SmartFileOrganizer


class SmartFileOrganizerTests(unittest.TestCase):
    def test_organize_folder_moves_files_into_expected_type_groups(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "photo.jpg").write_text("image", encoding="utf-8")
            (root / "notes.txt").write_text("text", encoding="utf-8")
            organizer = self._make_organizer(root)

            result = organizer.organize_folder(str(root), "type")
            organizer.close()

            self.assertEqual(result.moved_count, 2)
            self.assertTrue((root / "Images" / "photo.jpg").exists())
            self.assertTrue((root / "Documents" / "notes.txt").exists())

    def test_preview_and_organize_by_extension(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "report.pdf").write_text("pdf", encoding="utf-8")
            (root / "diagram.png").write_text("png", encoding="utf-8")
            organizer = self._make_organizer(root)

            preview = organizer.preview_organization(str(root), "extension")
            result = organizer.organize_folder(str(root), "extension")
            organizer.close()

            self.assertEqual([item.group_name for item in preview], ["PNG", "PDF"])
            self.assertEqual(result.moved_count, 2)
            self.assertTrue((root / "PDF" / "report.pdf").exists())
            self.assertTrue((root / "PNG" / "diagram.png").exists())

    def test_conflicting_names_are_renamed_safely(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            images = root / "Images"
            images.mkdir()
            (images / "photo.jpg").write_text("existing", encoding="utf-8")
            (root / "photo.jpg").write_text("new", encoding="utf-8")
            organizer = self._make_organizer(root)

            result = organizer.organize_folder(str(root), "type")
            organizer.close()

            self.assertEqual(result.moved_count, 1)
            self.assertTrue((images / "photo.jpg").exists())
            self.assertTrue((images / "photo_1.jpg").exists())

    def test_undo_last_run_restores_files_to_original_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            original_file = root / "script.py"
            original_file.write_text("print('hello')", encoding="utf-8")
            organizer = self._make_organizer(root)

            organizer.organize_folder(str(root), "type")
            restored_files = organizer.undo_last_run()
            organizer.close()

            self.assertEqual(len(restored_files), 1)
            self.assertTrue(original_file.exists())
            self.assertFalse((root / "Code" / "script.py").exists())

    def test_log_file_contains_move_information(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "track.mp3").write_text("music", encoding="utf-8")
            organizer = self._make_organizer(root)

            organizer.organize_folder(str(root), "type")
            organizer.close()

            log_content = (root / "logs" / "organizer.log").read_text(encoding="utf-8")
            self.assertIn("criterion=type", log_content)
            self.assertIn("track.mp3", log_content)
            self.assertIn("Audio", log_content)

    def test_stop_request_can_end_run_early(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for index in range(4):
                (root / f"file{index}.txt").write_text("text", encoding="utf-8")

            organizer = self._make_organizer(root)
            moved_count = {"value": 0}

            def on_move(_record) -> None:
                moved_count["value"] += 1

            result = organizer.organize_folder(
                str(root),
                "type",
                progress_callback=on_move,
                should_stop=lambda: moved_count["value"] >= 1,
            )
            organizer.close()

            self.assertTrue(result.stopped)
            self.assertEqual(result.moved_count, 1)

    def _make_organizer(self, root: Path) -> SmartFileOrganizer:
        return SmartFileOrganizer(
            history_path=str(root / "data" / "history.json"),
            log_path=str(root / "logs" / "organizer.log"),
        )


if __name__ == "__main__":
    unittest.main()
