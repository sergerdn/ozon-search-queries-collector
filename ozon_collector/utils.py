import os
import platform
from pathlib import Path


def get_chrome_executable_path():
    """Retrieve the Chrome executable path based on the operating system."""
    chrome_executable_path: Path
    match platform.system():
        case "Windows":
            chrome_executable_path = Path(
                "C:\Program Files\Google\Chrome\Application\chrome.exe"
            )
        case "Linux":
            chrome_executable_path = Path("/usr/bin/google-chrome")
        case _:
            raise FileNotFoundError(
                "Chrome executable not found for the current operating system."
            )

    assert chrome_executable_path.exists() and chrome_executable_path.is_file()

    return chrome_executable_path


def get_browser_profile_storage():
    """Retrieve the directory path for storing browser profiles from an environment variable.

    Raise an exception if the environment variable is not set.
    """
    storage_dir = os.getenv("BROWSER_PROFILE_STORAGE")
    if not storage_dir:
        raise EnvironmentError(
            "BROWSER_PROFILE_STORAGE environment variable is not set."
        )
    storage_dir = Path(storage_dir)
    assert storage_dir.exists() and storage_dir.is_dir()

    return storage_dir
