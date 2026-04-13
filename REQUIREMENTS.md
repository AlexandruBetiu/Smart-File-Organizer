# Requirements

This project stays simple and only uses Python standard library tools.
No extra package install is needed for the current version.

## Software Requirements
1. Python 3.10 or newer
2. `tkinter` available with Python for the GUI
3. Read and write permission for the folder you want to organize

## Functional Requirements
1. The program must scan files in one folder
2. The program must let the user choose the folder to organize
3. The program must sort files by chosen criteria
4. The program must create destination folders if they do not exist
5. The program must move files with `shutil.move()`
6. The program must log moved files with source, destination, and time
7. The program must support undo for the last run
8. The program must handle duplicate names and permission issues
9. The project must have a terminal version and a Tkinter GUI version

## What To Do First
1. Install Python if it is not already installed
2. Open terminal in the project folder
3. Run `python app.py` or `python gui_app.py`
4. Choose the folder
5. Choose the classify mode and start
