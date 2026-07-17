"""一次性探针：打印一条 CTA 策略 financials 的表头 token，用于填 FINANCIALS_COLS。
用法：uv run python scripts/probe_financials.py
"""
import sys

import requests

from cta_monitor.config import load_config

cfg = load_config("config.toml")
tok = requests.post(
    cfg.biyi.login_url,
    json={"userName": cfg.biyi.user, "passwd": cfg.biyi.passwd},
).json()["data"]["token"]
h = {"Authorization": f"Bearer {tok}"}

lst = requests.get(
    f"{cfg.biyi.base_url}/strategy/list?curPage=0&pageSize=100", headers=h
).json()["data"]
spec = next(
    s["strategySpec"] for s in lst
    if s["key"] in ("CTA", "CTA_EMS") and s["state"] == "RUNNING"
)
fin = requests.get(
    f"{cfg.biyi.base_url}/api/strategies/{spec}/financials", headers=h
).json()["data"]
print("strategySpec:", spec)
print("表头列（token|type）：")
for i, cell in enumerate(fin["tableData"][0].split(",")):
    print(f"  [{i}] {cell}")
print("首行数据：")
print(" ", fin["tableData"][1] if len(fin["tableData"]) > 1 else "(空)")
sys.exit(0)
