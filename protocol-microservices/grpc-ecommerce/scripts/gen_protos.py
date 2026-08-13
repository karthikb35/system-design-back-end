"""Generate gRPC Python stubs from the canonical protos in ``protos/``.

Why a script (not hand-written stubs)?
  The ``*_pb2.py`` (messages) and ``*_pb2_grpc.py`` (service stubs) files are
  *generated* from the ``.proto`` contracts. Regenerating guarantees the code
  always matches the contract.

Each target gets only the protos it needs:
  - users service  -> users
  - products svc   -> products
  - orders service -> users, products, orders  (it calls the first two)
  - gateway        -> users, products, orders  (it calls all three)

Import quirk we handle:
  protoc emits ``import users_pb2 as ...`` (a flat, top-level import) inside the
  generated ``*_pb2_grpc.py``. For that to resolve when the stubs live in a
  package like ``app/pb/``, each ``pb`` folder's ``__init__.py`` prepends its own
  directory to ``sys.path`` (see the generated ``__init__`` below).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROTO_DIR = ROOT / "protos"

# target package dir -> list of proto module names to generate into it
TARGETS: dict[str, list[str]] = {
    "services/users/app/pb": ["users"],
    "services/products/app/pb": ["products"],
    "services/orders/app/pb": ["users", "products", "orders"],
    "gateway/app/pb": ["users", "products", "orders"],
}

_INIT_SHIM = (
    '"""Generated gRPC stubs package.\n\n'
    "Adds this directory to sys.path so the generated ``*_pb2_grpc`` modules can\n"
    'resolve their flat ``import *_pb2`` statements."""\n'
    "import os\n"
    "import sys\n\n"
    "sys.path.insert(0, os.path.dirname(__file__))\n"
)


def generate() -> None:
    for target, protos in TARGETS.items():
        out = ROOT / target
        out.mkdir(parents=True, exist_ok=True)
        (out / "__init__.py").write_text(_INIT_SHIM, encoding="utf-8")

        proto_files = [str(PROTO_DIR / f"{name}.proto") for name in protos]
        cmd = [
            sys.executable,
            "-m",
            "grpc_tools.protoc",
            f"-I{PROTO_DIR}",
            f"--python_out={out}",
            f"--grpc_python_out={out}",
            *proto_files,
        ]
        print("generating", target, "<-", protos)
        subprocess.run(cmd, check=True)


if __name__ == "__main__":
    generate()
    print("done.")
