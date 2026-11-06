import os
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pymssql

ROOT = Path(__file__).resolve().parent.parent


def _load_env():
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def connect():
    _load_env()
    return pymssql.connect(
        server=os.environ["DB_SERVER"], port=int(os.environ.get("DB_PORT", 1433)),
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"], login_timeout=20, timeout=600, charset="UTF-8")


def query(sql, params=None):
    with connect() as c:
        cur = c.cursor()
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=cols)
    for col in df.columns:
        if len(df) and df[col].map(lambda x: isinstance(x, Decimal)).any():
            df[col] = df[col].astype(float)
    return df
