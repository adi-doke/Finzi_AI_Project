from __future__ import annotations

import site
import sys
from pathlib import Path


repo_root = Path(__file__).resolve().parent.parent
runtime_zip = repo_root / "runtime.zip"
if runtime_zip.exists() and str(runtime_zip) not in sys.path:
    sys.path.insert(0, str(runtime_zip))

repo_vendor = repo_root / "vendor"
if repo_vendor.exists() and str(repo_vendor) not in sys.path:
    sys.path.insert(1, str(repo_vendor))

user_site = site.getusersitepackages()
if user_site and user_site not in sys.path:
    site.addsitedir(user_site)
