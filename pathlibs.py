import os
from pathlib import Path

print()
print("__file__:", __file__)
print()
print("os.path.abspath(__file__):", os.path.abspath(__file__))
print()

# Print current working directory for context
print("Current working directory:", os.getcwd())
print()


script_path = Path(__file__)
print("Path(__file__):", script_path)
print("script_path.resolve():", script_path.resolve())
print("script_path.absolute():", script_path.absolute())
print("Current working directory:", Path.cwd())

# To demonstrate symlink behavior
print("Is symlink:", script_path.is_symlink())
if script_path.is_symlink():
    print("Symlink target:", script_path.resolve())
