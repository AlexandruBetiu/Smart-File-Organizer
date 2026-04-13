# Solution

The solution is an OOP Python app with one main organizer class used by both interfaces.
One version works in the terminal and one version works in a Tkinter window with a cleaner modern layout.

## How It Works
1. The user selects or types a folder path
2. The user chooses how the files should be classified
3. The organizer scans files and builds the target folders
4. Files are moved with `shutil.move()`
5. Every move is saved in log and history files
6. The last organize action can be undone

## How To Operate It
1. Run `python app.py` for the terminal version
2. Run `python gui_app.py` for the window version
3. Pick a folder
4. Choose `type`, `extension`, or `date`
5. Start organizing
6. Use stop in the GUI if needed
7. Use undo if you want to restore the last moved files

## Extra Files
1. `README.md` for quick project overview
2. `PLAN.md` for the basic idea and steps
3. `REQUIREMENTS.md` for software and project needs
4. `PROJECT_STRUCTURE.md` for the main file map
