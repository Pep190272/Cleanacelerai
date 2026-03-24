================================================================================
  CLEANACELERAI PRO
  Windows Desktop Utility for File Management & Cleanup
================================================================================

DESCRIPTION
-----------
Cleanacelerai PRO is a Windows desktop application that helps you keep your
system clean and organized. It combines duplicate detection, junk cleanup,
bookmark management, bulk renaming, and AI-powered file organization advice
into a single, clean interface.


FEATURES
--------
  - Duplicate Finder     : Detect and remove duplicate files by content hash
  - Temp/Junk Cleaner    : Free up disk space by removing temporary files
  - Bookmark Manager     : Clean and manage bookmarks for Chrome, Edge & Brave
  - Bulk Renamer         : Rename multiple files using patterns and rules
  - Chaos Advisor        : AI-powered suggestions for organizing your files
  - Protection Rules     : Define rules to prevent accidental deletion of
                           important files


REQUIREMENTS
------------
  - Windows 10 or 11 (64-bit)
  - Python 3.10 or higher  (for development)
  - pip dependencies:  see requirements.txt


DEVELOPMENT SETUP
-----------------
  1. Clone or download the project.

  2. (Recommended) Create and activate a virtual environment:
       python -m venv .venv
       .venv\Scripts\activate

  3. Install dependencies:
       pip install -r requirements.txt

  4. Run the application:
       python cleanacelerai/run.py


BUILD THE EXECUTABLE
--------------------
  To produce a standalone .exe using PyInstaller:

       pyinstaller cleanacelerai.spec

  The output will be in the dist\ folder.

  Note: make sure all dependencies are installed before building.


RUNNING TESTS
-------------
  Tests use pytest. Run them from the project root:

       cd cleanacelerai
       python -m pytest tests/

  Add -v for verbose output:

       python -m pytest tests/ -v


CONFIGURATION FILE
------------------
  User settings and protection rules are stored in:

       %USERPROFILE%\.cleanacelerai\config.json

  (e.g. C:\Users\YourName\.cleanacelerai\config.json)

  The file is created automatically on first run. You can edit it manually,
  but it is recommended to use the in-app Settings panel.


CREDITS & ATTRIBUTIONS
-----------------------
  Application icon downloaded from https://icon-icons.com


================================================================================
