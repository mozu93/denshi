import hashlib
import logging

logger = logging.getLogger(__name__)

def get_file_hash(file_path):
    """Calculates the SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()
    except FileNotFoundError:
        return None
    except Exception as e:
        logger.error(f"ハッシュ計算に失敗しました {file_path}: {e}")
        return None
