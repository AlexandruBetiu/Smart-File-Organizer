import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from organizer.models import MoveRecord, OrganizationResult
from organizer.organizer import SmartFileOrganizer


class OrganizerGUI:
    COLORS = {
        "bg": "#141B37",
        "panel": "#1D2854",
        "card": "#243261",
        "card_soft": "#1B244A",
        "text": "#F4F7FF",
        "muted": "#9CA9D1",
        "cyan": "#66E3FF",
        "pink": "#FF869A",
        "warm": "#FFB56B",
        "button": "#31428A",
        "button_hover": "#4055AA",
        "danger": "#9F4265",
    }

    def __init__(self) -> None:
        self.organizer = SmartFileOrganizer()
        self.root = tk.Tk()
        self.root.title("Smart File Organizer")
        self.root.geometry("1000x620")
        self.root.minsize(920, 560)
        self.root.configure(bg=self.COLORS["bg"])
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.selected_folder = tk.StringVar()
        self.selected_criterion = tk.StringVar(value="type")
        self.status_text = tk.StringVar(value="Choose a folder, then preview or organize it.")
        self.files_count_text = tk.StringVar(value="0")
        self.groups_count_text = tk.StringVar(value="0")
        self.mode_text = tk.StringVar(value="File type")
        self.last_action_text = tk.StringVar(value="0")

        self.worker_thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.worker_queue: queue.Queue[tuple[str, object]] = queue.Queue()

        self._configure_styles()
        self._build_layout()
        self.root.after(120, self._poll_worker_queue)

    def _configure_styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Organizer.TCombobox",
            fieldbackground=self.COLORS["card"],
            background=self.COLORS["button"],
            foreground=self.COLORS["text"],
            arrowcolor=self.COLORS["text"],
            bordercolor=self.COLORS["cyan"],
            lightcolor=self.COLORS["card"],
            darkcolor=self.COLORS["card"],
        )

    def _build_layout(self) -> None:
        shell = tk.Frame(self.root, bg=self.COLORS["bg"], padx=22, pady=22)
        shell.pack(fill="both", expand=True)

        sidebar = tk.Frame(
            shell,
            bg=self.COLORS["panel"],
            width=260,
            padx=18,
            pady=18,
            highlightbackground=self.COLORS["cyan"],
            highlightthickness=1,
        )
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        content = tk.Frame(shell, bg=self.COLORS["bg"])
        content.pack(side="left", fill="both", expand=True, padx=(18, 0))

        self._build_sidebar(sidebar)
        self._build_content(content)

    def _build_sidebar(self, parent: tk.Frame) -> None:
        tk.Label(
            parent,
            text="Smart File\nOrganizer",
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
            justify="left",
            font=("Segoe UI Semibold", 22),
        ).pack(anchor="w")

        tk.Label(
            parent,
            text="Simple file sorting with preview, history, and undo.",
            bg=self.COLORS["panel"],
            fg=self.COLORS["muted"],
            justify="left",
            wraplength=210,
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(10, 22))

        self._make_button(parent, "Choose Folder", self._choose_folder, self.COLORS["button"]).pack(fill="x")
        self._make_button(parent, "Scan Preview", self._scan_preview, self.COLORS["card"]).pack(fill="x", pady=(10, 0))
        self._make_button(parent, "Organize Options", self._open_organize_popup, self.COLORS["warm"]).pack(fill="x", pady=(10, 0))
        self._make_button(parent, "Undo Last Run", self._undo_last_run, self.COLORS["card"]).pack(fill="x", pady=(10, 0))
        self.stop_button = self._make_button(parent, "Stop", self._stop_organize, self.COLORS["danger"])
        self.stop_button.pack(fill="x", pady=(10, 0))
        self.stop_button.configure(state="disabled")

        info_card = self._make_card(parent, "Current Mode")
        info_card.pack(fill="x", pady=(26, 0))
        tk.Label(
            info_card,
            textvariable=self.mode_text,
            bg=self.COLORS["card_soft"],
            fg=self.COLORS["text"],
            anchor="w",
            font=("Segoe UI Semibold", 12),
        ).pack(fill="x")

        folder_card = self._make_card(parent, "Selected Folder")
        folder_card.pack(fill="x", pady=(14, 0))
        tk.Label(
            folder_card,
            textvariable=self.selected_folder,
            bg=self.COLORS["card_soft"],
            fg=self.COLORS["muted"],
            anchor="w",
            justify="left",
            wraplength=210,
            font=("Consolas", 9),
        ).pack(fill="x")

    def _build_content(self, parent: tk.Frame) -> None:
        header_card = self._make_card(parent, "Workspace", accent=self.COLORS["pink"])
        header_card.pack(fill="x")
        tk.Label(
            header_card,
            text="Review the folder first, then start from the popup so the main window stays clean.",
            bg=self.COLORS["card_soft"],
            fg=self.COLORS["text"],
            anchor="w",
            justify="left",
            font=("Segoe UI", 11),
        ).pack(fill="x")

        stats_row = tk.Frame(parent, bg=self.COLORS["bg"])
        stats_row.pack(fill="x", pady=(18, 0))

        self._build_stat_card(stats_row, "Files Found", self.files_count_text, self.COLORS["cyan"]).pack(side="left", fill="both", expand=True)
        self._build_stat_card(stats_row, "Groups Planned", self.groups_count_text, self.COLORS["pink"]).pack(side="left", fill="both", expand=True, padx=12)
        self._build_stat_card(stats_row, "Last Run Moved", self.last_action_text, self.COLORS["warm"]).pack(side="left", fill="both", expand=True)

        preview_card = self._make_card(parent, "Preview", accent=self.COLORS["cyan"])
        preview_card.pack(fill="both", expand=True, pady=(18, 0))

        self.preview_box = tk.Text(
            preview_card,
            height=16,
            bg=self.COLORS["card_soft"],
            fg=self.COLORS["text"],
            insertbackground=self.COLORS["text"],
            relief="flat",
            wrap="word",
            font=("Consolas", 10),
            padx=10,
            pady=10,
        )
        self.preview_box.pack(fill="both", expand=True)
        self.preview_box.insert("1.0", "No preview yet.\nChoose a folder and click Scan Preview.")
        self.preview_box.configure(state="disabled")

        status_card = self._make_card(parent, "Status", accent=self.COLORS["warm"])
        status_card.pack(fill="x", pady=(18, 0))
        tk.Label(
            status_card,
            textvariable=self.status_text,
            bg=self.COLORS["card_soft"],
            fg=self.COLORS["text"],
            anchor="w",
            justify="left",
            wraplength=650,
            font=("Segoe UI", 10),
        ).pack(fill="x")

    def _make_card(self, parent: tk.Widget, title: str, accent: str | None = None) -> tk.Frame:
        frame = tk.Frame(
            parent,
            bg=self.COLORS["card_soft"],
            padx=16,
            pady=14,
            highlightbackground=accent or self.COLORS["card"],
            highlightthickness=1,
        )
        tk.Label(
            frame,
            text=title.upper(),
            bg=self.COLORS["card_soft"],
            fg=accent or self.COLORS["muted"],
            anchor="w",
            font=("Segoe UI Semibold", 9),
        ).pack(fill="x", pady=(0, 8))
        return frame

    def _build_stat_card(self, parent: tk.Frame, title: str, variable: tk.StringVar, accent: str) -> tk.Frame:
        card = tk.Frame(
            parent,
            bg=self.COLORS["panel"],
            padx=16,
            pady=14,
            highlightbackground=accent,
            highlightthickness=1,
        )
        tk.Label(
            card,
            text=title.upper(),
            bg=self.COLORS["panel"],
            fg=self.COLORS["muted"],
            anchor="w",
            font=("Segoe UI Semibold", 9),
        ).pack(fill="x")
        tk.Label(
            card,
            textvariable=variable,
            bg=self.COLORS["panel"],
            fg=self.COLORS["text"],
            anchor="w",
            font=("Segoe UI Semibold", 24),
        ).pack(fill="x", pady=(8, 0))
        return card

    def _make_button(self, parent: tk.Widget, text: str, command, bg: str) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=self.COLORS["text"],
            activebackground=self.COLORS["button_hover"],
            activeforeground=self.COLORS["text"],
            relief="flat",
            bd=0,
            padx=14,
            pady=12,
            font=("Segoe UI Semibold", 10),
            cursor="hand2",
        )

    def _choose_folder(self) -> None:
        folder = filedialog.askdirectory()
        if not folder:
            return

        self.selected_folder.set(folder)
        self._set_status(f"Selected folder: {folder}")
        self._scan_preview(update_status=False)

    def _scan_preview(self, update_status: bool = True) -> None:
        folder = self.selected_folder.get().strip()
        if not folder:
            messagebox.showwarning("Missing folder", "Please choose a folder first.")
            return

        try:
            preview = self.organizer.preview_organization(folder, self.selected_criterion.get())
            summary = self.organizer.summarize_preview(folder, self.selected_criterion.get())
        except (FileNotFoundError, NotADirectoryError, ValueError) as error:
            messagebox.showerror("Error", str(error))
            return

        self.files_count_text.set(str(len(preview)))
        self.groups_count_text.set(str(len(summary)))
        self.mode_text.set(self.organizer.get_criteria()[self.selected_criterion.get()])

        if not preview:
            self._render_preview(["No files found in the selected folder."])
            if update_status:
                self._set_status("Folder scanned. No files to organize.")
            return

        lines = ["Planned groups:"]
        for group_name, count in summary.items():
            lines.append(f"- {group_name}: {count}")

        lines.append("")
        lines.append("First files in preview:")
        for item in preview[:12]:
            lines.append(f"- {item.file_name} -> {item.group_name}")

        if len(preview) > 12:
            lines.append(f"- ... and {len(preview) - 12} more")

        self._render_preview(lines)
        if update_status:
            self._set_status("Preview updated.")

    def _open_organize_popup(self) -> None:
        if not self.selected_folder.get().strip():
            messagebox.showwarning("Missing folder", "Please choose a folder first.")
            return

        popup = tk.Toplevel(self.root)
        popup.title("Organize Options")
        popup.geometry("360x220")
        popup.resizable(False, False)
        popup.configure(bg=self.COLORS["panel"])
        popup.transient(self.root)
        popup.grab_set()

        card = tk.Frame(
            popup,
            bg=self.COLORS["card_soft"],
            padx=18,
            pady=18,
            highlightbackground=self.COLORS["cyan"],
            highlightthickness=1,
        )
        card.pack(fill="both", expand=True, padx=18, pady=18)

        tk.Label(
            card,
            text="Choose how to classify the files",
            bg=self.COLORS["card_soft"],
            fg=self.COLORS["text"],
            anchor="w",
            font=("Segoe UI Semibold", 12),
        ).pack(fill="x")

        tk.Label(
            card,
            text="The selected option will decide the folder names that get created.",
            bg=self.COLORS["card_soft"],
            fg=self.COLORS["muted"],
            justify="left",
            wraplength=300,
            font=("Segoe UI", 10),
        ).pack(fill="x", pady=(8, 14))

        criteria = self.organizer.get_criteria()
        label_to_key = {label: key for key, label in criteria.items()}
        selected_label = tk.StringVar(value=criteria[self.selected_criterion.get()])

        dropdown = ttk.Combobox(
            card,
            textvariable=selected_label,
            values=list(label_to_key),
            state="readonly",
            style="Organizer.TCombobox",
            font=("Segoe UI", 10),
        )
        dropdown.pack(fill="x")

        actions = tk.Frame(card, bg=self.COLORS["card_soft"])
        actions.pack(fill="x", pady=(18, 0))

        tk.Button(
            actions,
            text="Cancel",
            command=popup.destroy,
            bg=self.COLORS["card"],
            fg=self.COLORS["text"],
            relief="flat",
            bd=0,
            padx=12,
            pady=10,
            font=("Segoe UI Semibold", 10),
            cursor="hand2",
        ).pack(side="left", fill="x", expand=True)

        tk.Button(
            actions,
            text="Start",
            command=lambda: self._start_organize(label_to_key[selected_label.get()], popup),
            bg=self.COLORS["warm"],
            fg=self.COLORS["bg"],
            relief="flat",
            bd=0,
            padx=12,
            pady=10,
            font=("Segoe UI Semibold", 10),
            cursor="hand2",
        ).pack(side="left", fill="x", expand=True, padx=(10, 0))

    def _start_organize(self, criterion: str, popup: tk.Toplevel) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showinfo("Busy", "Organization is already running.")
            return

        folder = self.selected_folder.get().strip()
        if not folder:
            messagebox.showwarning("Missing folder", "Please choose a folder first.")
            return

        self.selected_criterion.set(criterion)
        self.mode_text.set(self.organizer.get_criteria()[criterion])
        self.stop_event.clear()
        self.stop_button.configure(state="normal")
        self._set_status("Organization started...")
        self._render_preview(["Working...", f"Folder: {folder}", f"Mode: {self.mode_text.get()}"])

        popup.destroy()

        self.worker_thread = threading.Thread(
            target=self._organize_worker,
            args=(folder, criterion),
            daemon=True,
        )
        self.worker_thread.start()

    def _organize_worker(self, folder: str, criterion: str) -> None:
        try:
            result = self.organizer.organize_folder(
                folder,
                criterion,
                progress_callback=lambda record: self.worker_queue.put(("move", record)),
                should_stop=self.stop_event.is_set,
            )
            self.worker_queue.put(("done", result))
        except Exception as error:
            self.worker_queue.put(("error", str(error)))

    def _stop_organize(self) -> None:
        if not self.worker_thread or not self.worker_thread.is_alive():
            self._set_status("Nothing is running right now.")
            self.stop_button.configure(state="disabled")
            return

        self.stop_event.set()
        self._set_status("Stop requested. Finishing the current file if needed.")

    def _undo_last_run(self) -> None:
        restored_files = self.organizer.undo_last_run()
        if restored_files:
            self.last_action_text.set(str(len(restored_files)))
            self._render_preview(self._move_lines(restored_files, title="Restored files"))
            self._set_status(f"Undo complete. Restored {len(restored_files)} file(s).")
            self._scan_preview(update_status=False)
        else:
            self._set_status("Nothing to undo.")

    def _poll_worker_queue(self) -> None:
        while not self.worker_queue.empty():
            event, payload = self.worker_queue.get()
            if event == "move":
                self._handle_move_event(payload)
            elif event == "done":
                self._handle_done_event(payload)
            elif event == "error":
                self.stop_button.configure(state="disabled")
                messagebox.showerror("Error", str(payload))
                self._set_status("Organization failed.")

        self.root.after(120, self._poll_worker_queue)

    def _handle_move_event(self, record: MoveRecord) -> None:
        current_lines = self._get_preview_lines()
        if len(current_lines) > 18:
            current_lines = current_lines[:18]
        current_lines.append(f"Moved: {Path(record.source).name} -> {record.group_name}")
        self._render_preview(current_lines[-20:])

    def _handle_done_event(self, result: OrganizationResult) -> None:
        self.stop_button.configure(state="disabled")
        self.last_action_text.set(str(result.moved_count))
        self._scan_preview(update_status=False)

        if result.moved_files:
            self._render_preview(self._move_lines(result.moved_files, title="Moved files"))

        if result.errors:
            lines = self._get_preview_lines()
            lines.append("")
            lines.append("Errors:")
            for message in result.errors:
                lines.append(f"- {message}")
            self._render_preview(lines)

        if result.stopped:
            self._set_status(f"Stopped. {result.moved_count} file(s) were moved before stop.")
        else:
            self._set_status(f"Done. Moved {result.moved_count} file(s).")

    def _move_lines(self, records: list[MoveRecord], title: str) -> list[str]:
        lines = [title + ":"]
        for record in records[:16]:
            lines.append(f"- {Path(record.source).name} -> {Path(record.destination).parent.name}")
        if len(records) > 16:
            lines.append(f"- ... and {len(records) - 16} more")
        return lines

    def _render_preview(self, lines: list[str]) -> None:
        self.preview_box.configure(state="normal")
        self.preview_box.delete("1.0", tk.END)
        self.preview_box.insert("1.0", "\n".join(lines))
        self.preview_box.configure(state="disabled")

    def _get_preview_lines(self) -> list[str]:
        text = self.preview_box.get("1.0", tk.END).strip()
        if not text:
            return []
        return text.splitlines()

    def _set_status(self, message: str) -> None:
        self.status_text.set(message)

    def _on_close(self) -> None:
        self.stop_event.set()
        self.organizer.close()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def run_gui() -> None:
    OrganizerGUI().run()
