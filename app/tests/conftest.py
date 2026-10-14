"""Configuración compartida de pruebas.

Las variables de entorno se fijan antes de importar la aplicación porque
`Settings` y el engine se construyen al importar los módulos.
"""

import os
import tempfile

_TMP_DB = os.path.join(tempfile.mkdtemp(prefix="petpulse-test-"), "test.db")
os.environ["DATABASE_URL_ASYNC"] = f"sqlite+aiosqlite:///{_TMP_DB}"
os.environ["SUPABASE_URL"] = "https://test-project.supabase.co"
os.environ.pop("SUPABASE_JWT_SECRET", None)
