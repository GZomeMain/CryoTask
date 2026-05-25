import PyInstaller.__main__
import os
import sys

# 1. Define the separator (Windows uses ';')
separator = ";" 

# 2. Define the arguments
args = [
    'main.py',                                  # Entry point
    '--name=CryoTask',                          # Name of the exe
    '--noconsole',                              # Hide the command console window
    '--onefile',                                # Bundle everything into one file
    f'--add-data=src/cryotask/ui/web/{separator}src/cryotask/ui/web/', # Web GUI assets
    f'--add-data=assets/{separator}assets/',    # App assets (icons, etc)
    '--icon=assets/app_icon.ico',               # Application icon
    '--uac-admin',                              # Request admin rights (needed for RAM EmptyWorkingSet)
    '--clean',                                  # Clean PyInstaller cache
]

# 3. Run PyInstaller
print("❄️  Freezing CryoTask (Web GUI) into an Exe... This may take a minute.")
PyInstaller.__main__.run(args)