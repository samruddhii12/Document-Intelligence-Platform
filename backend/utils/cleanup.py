import shutil
import os


def delete_session_folder(session_path: str):
    """
    Delete the entire session folder safely.
    """
    if os.path.exists(session_path):
        shutil.rmtree(session_path)
        return True
    return False