import PyInstaller.__main__
import customtkinter
import os
import sys

# 1. Get the path to CustomTkinter so we can bundle it
ctk_path = os.path.dirname(customtkinter.__file__)

# 2. Define the separator (Windows uses ';')
separator = ";" 

# 3. Define the arguments
args = [
    'main.py',                                  # Your script
    '--name=CryoTask',                          # Name of the exe
    '--noconsole',                              # Hide the black command window
    '--onefile',                                # Bundle everything into one file
    f'--add-data={ctk_path}{separator}customtkinter/', # Include CTK themes
    '--icon=assets/app_icon.ico',               # Use the icon we just made
    '--uac-admin',                              # Request Admin rights (NEEDED for RAM trimming)
    '--clean',                                  # Clean cache
]

# 4. Run PyInstaller
print("❄️  Freezing CryoTask into an Exe... This may take a minute.")
PyInstaller.__main__.run(args)