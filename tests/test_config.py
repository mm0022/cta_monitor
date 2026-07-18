from cta_monitor.config import load_config


def test_load_config(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text(
        """
[postgres]
host="h"
port="1"
user="u"
password="pw"
database="shiji"
[biyi]
login_url="lu"
base_url="bu"
user="bu2"
passwd="pp"
[datahub]
gateway_url="g"
api_key="k"
prefix="CYBERX_PROD"
[slack]
webhook_url="https://hooks.slack.com/services/x"
[monitor]
accounts=["a1"]
min_notional_u=10.0
freshness_hours=1.0
[portfolio_accounts]
accP="xs_carry_daily"
""",
        encoding="utf-8",
    )
    cfg = load_config(str(p))
    assert cfg.pg.database == "shiji"
    assert cfg.datahub.prefix == "CYBERX_PROD"
    assert cfg.accounts == ("a1",)
    assert cfg.min_notional_u == 10.0
    assert cfg.portfolio_accounts == {"accP": "xs_carry_daily"}
