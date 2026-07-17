from cta_monitor.datahub import datahub_key


def test_datahub_key():
    assert datahub_key("CYBERX_PROD", "binance_tokyo_cta_momentum_test1_new", "btc") == (
        "CYBERX_PROD-CTA_SIGNAL_PUBLISHER-LAST_PUBLISHED_V1-"
        "binance_tokyo_cta_momentum_test1_new-btc"
    )
