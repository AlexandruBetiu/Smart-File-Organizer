from organizer.organizer import SmartFileOrganizer


class OrganizerCLI:
    def __init__(self) -> None:
        self.organizer = SmartFileOrganizer()
        self.selected_folder = ""
        self.selected_criterion = "type"

    def start(self) -> None:
        try:
            while True:
                self._print_menu()
                choice = input("Choose an option: ").strip()

                if choice == "1":
                    self._select_folder()
                elif choice == "2":
                    self._choose_criterion()
                elif choice == "3":
                    self._scan_folder()
                elif choice == "4":
                    self._organize_folder()
                elif choice == "5":
                    self._undo_last_run()
                elif choice == "6":
                    print("Goodbye.")
                    break
                else:
                    print("Invalid option. Try again.")
        finally:
            self.organizer.close()

    def _print_menu(self) -> None:
        criteria_label = self.organizer.get_criteria()[self.selected_criterion]
        current_folder = self.selected_folder or "No folder selected"
        print("\nSmart File Organizer")
        print(f"Current folder: {current_folder}")
        print(f"Classify by: {criteria_label}")
        print("1. Choose folder")
        print("2. Choose classify mode")
        print("3. Scan and preview")
        print("4. Organize folder")
        print("5. Undo last organize")
        print("6. Exit")

    def _select_folder(self) -> None:
        folder_path = input("Enter folder path: ").strip()
        try:
            self.organizer.scan_folder(folder_path)
            self.selected_folder = folder_path
            print(f"Folder selected: {folder_path}")
        except (FileNotFoundError, NotADirectoryError) as error:
            print(error)

    def _choose_criterion(self) -> None:
        criteria = self.organizer.get_criteria()
        print("\nClassify options:")
        for index, (key, label) in enumerate(criteria.items(), start=1):
            print(f"{index}. {label} ({key})")

        choice = input("Choose classify mode: ").strip()
        keys = list(criteria)

        if choice.isdigit() and 1 <= int(choice) <= len(keys):
            self.selected_criterion = keys[int(choice) - 1]
            print(f"Classify mode set to: {criteria[self.selected_criterion]}")
            return

        if choice in criteria:
            self.selected_criterion = choice
            print(f"Classify mode set to: {criteria[self.selected_criterion]}")
            return

        print("Invalid classify mode.")

    def _scan_folder(self) -> None:
        if not self._ensure_folder_selected():
            return

        try:
            files = self.organizer.scan_folder(self.selected_folder)
            preview = self.organizer.preview_organization(self.selected_folder, self.selected_criterion)
            summary = self.organizer.summarize_preview(self.selected_folder, self.selected_criterion)
        except (FileNotFoundError, NotADirectoryError, ValueError) as error:
            print(error)
            return

        print(f"\nFound {len(files)} file(s).")
        if not files:
            return

        print("Preview:")
        for item in preview[:10]:
            print(f"- {item.file_name} -> {item.group_name}")

        if len(preview) > 10:
            print(f"- ... and {len(preview) - 10} more file(s)")

        print("Summary:")
        for group_name, count in summary.items():
            print(f"- {group_name}: {count}")

    def _organize_folder(self) -> None:
        if not self._ensure_folder_selected():
            return

        try:
            result = self.organizer.organize_folder(self.selected_folder, self.selected_criterion)
        except (FileNotFoundError, NotADirectoryError, ValueError) as error:
            print(error)
            return

        if result.moved_files:
            print(f"Moved {result.moved_count} file(s) using {self.selected_criterion} classification.")
        else:
            print("No files were moved.")

        if result.errors:
            print("Errors:")
            for message in result.errors:
                print(f"- {message}")

    def _undo_last_run(self) -> None:
        restored_files = self.organizer.undo_last_run()
        if restored_files:
            print(f"Restored {len(restored_files)} file(s).")
        else:
            print("There is no history to undo.")

    def _ensure_folder_selected(self) -> bool:
        if self.selected_folder:
            return True
        print("Choose a folder first.")
        return False


def run_cli() -> None:
    OrganizerCLI().start()
