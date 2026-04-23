import os

# Define the expected structure as a dictionary
expected_structure = {
    "trading_bot_template": [
        ".env",
        "requirements.txt",
        "monitor_and_import.py",
        "import.py",
        "data/",
        "logs/",
        "config/cronitor_config.yaml",
        "src/__init__.py",
        "src/db_operations.py",
        "src/file_handler.py",
        "src/notification.py",
        "src/cronitor_monitoring.py",
        "README.md"
    ]
}

# Path to the main project directory (change this path if needed)
project_path = "/Users/danieldeenik/Documents/Projects/trading_bot_template"

# Function to check the file structure
def check_project_structure(project_path, expected_structure):
    missing_files = []
    for folder, files in expected_structure.items():
        folder_path = os.path.join(project_path, folder)
        for file in files:
            file_path = os.path.join(folder_path, file)
            if not os.path.exists(file_path):
                missing_files.append(file_path)
    return missing_files

# Run the check
missing_files = check_project_structure(project_path, expected_structure)

# Display result
if missing_files:
    print("The following files or directories are missing:")
    for missing in missing_files:
        print(missing)
else:
    print("All expected files and directories are present.")
