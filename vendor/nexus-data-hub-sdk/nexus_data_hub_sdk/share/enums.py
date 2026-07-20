from enum import Enum

from nexus_data_hub_sdk.exception.exceptions import ParamInvalidError


class DataType(Enum):
    KLINE_1M = 'KLINE_1M'
    KLINE_3M = 'KLINE_3M'
    KLINE_5M = 'KLINE_5M'
    KLINE_15M = 'KLINE_15M'
    KLINE_30M = 'KLINE_30M'
    KLINE_1H = 'KLINE_1H'
    KLINE_2H = 'KLINE_2H'
    KLINE_4H = 'KLINE_4H'
    KLINE_8H = 'KLINE_8H'
    KLINE_12H = 'KLINE_12H'
    KLINE_1D = 'KLINE_1D'
    INDEX_PRICE_1M = 'INDEX_PRICE_1M'
    INDEX_PRICE_3M = 'INDEX_PRICE_3M'
    INDEX_PRICE_5M = 'INDEX_PRICE_5M'
    INDEX_PRICE_15M = 'INDEX_PRICE_15M'
    INDEX_PRICE_30M = 'INDEX_PRICE_30M'
    INDEX_PRICE_1H = 'INDEX_PRICE_1H'
    INDEX_PRICE_2H = 'INDEX_PRICE_2H'
    INDEX_PRICE_4H = 'INDEX_PRICE_4H'
    INDEX_PRICE_8H = 'INDEX_PRICE_8H'
    INDEX_PRICE_12H = 'INDEX_PRICE_12H'
    INDEX_PRICE_1D = 'INDEX_PRICE_1D'
    MARK_PRICE_1M = 'MARK_PRICE_1M'
    MARK_PRICE_3M = 'MARK_PRICE_3M'
    MARK_PRICE_5M = 'MARK_PRICE_5M'
    MARK_PRICE_15M = 'MARK_PRICE_15M'
    MARK_PRICE_30M = 'MARK_PRICE_30M'
    MARK_PRICE_1H = 'MARK_PRICE_1H'
    MARK_PRICE_2H = 'MARK_PRICE_2H'
    MARK_PRICE_4H = 'MARK_PRICE_4H'
    MARK_PRICE_8H = 'MARK_PRICE_8H'
    MARK_PRICE_12H = 'MARK_PRICE_12H'
    MARK_PRICE_1D = 'MARK_PRICE_1D'
    PREMIUM_INDEX_1M = 'PREMIUM_INDEX_1M'
    PREMIUM_INDEX_3M = 'PREMIUM_INDEX_3M'
    PREMIUM_INDEX_5M = 'PREMIUM_INDEX_5M'
    PREMIUM_INDEX_15M = 'PREMIUM_INDEX_15M'
    PREMIUM_INDEX_30M = 'PREMIUM_INDEX_30M'
    PREMIUM_INDEX_1H = 'PREMIUM_INDEX_1H'
    PREMIUM_INDEX_2H = 'PREMIUM_INDEX_2H'
    PREMIUM_INDEX_4H = 'PREMIUM_INDEX_4H'
    PREMIUM_INDEX_8H = 'PREMIUM_INDEX_8H'
    PREMIUM_INDEX_12H = 'PREMIUM_INDEX_12H'
    PREMIUM_INDEX_1D = 'PREMIUM_INDEX_1D'
    FUNDING_RATE = 'FUNDING_RATE'
    FUNDING_RATE_10M = 'FUNDING_RATE_10M'
    INTEREST_RATE = 'INTEREST_RATE'
    OPEN_INTEREST_1H = 'OPEN_INTEREST_1H'
    HAIRCUT = 'HAIRCUT'
    HAIRCUT_DE = "HAIRCUT_DE"
    PM_COLLATERAL_RATIO = "PM_COLLATERAL_RATIO"
    MMR = 'MMR'
    MMD = 'MMD'
    STAKING_RATE = "STAKING_RATE"
    INSURANCE_FUND = "INSURANCE_FUND"
    NOTEBOOK = 'NOTEBOOK'
    STREAMING = 'STREAMING'
    SEQUENCED = 'SEQUENCED'
    OPTIONS_25DELTA_SKEW_10M = 'OPTIONS_25DELTA_SKEW_10M'
    OPTIONS_25DELTA_SKEW_1H = 'OPTIONS_25DELTA_SKEW_1H'
    OPTIONS_25DELTA_SKEW_24H = 'OPTIONS_25DELTA_SKEW_24H'
    FUT_EST_LEVG_RATIO_1H = 'FUT_EST_LEVG_RATIO_1H'
    CASH_MARG_FUT_OPEN_INTEREST_NATIVE_1H = 'CASH_MARG_FUT_OPEN_INTEREST_NATIVE_1H'
    CASH_MARG_FUT_OPEN_INTEREST_USD_1H = 'CASH_MARG_FUT_OPEN_INTEREST_USD_1H'
    FUT_LONG_LIQ_NATIVE_TOTAL_1H = 'FUT_LONG_LIQ_NATIVE_TOTAL_1H'
    FUT_SHORT_LIQ_NATIVE_TOTAL_1H = 'FUT_SHORT_LIQ_NATIVE_TOTAL_1H'
    FUT_LONG_LIQ_USD_TOTAL_1H = 'FUT_LONG_LIQ_USD_TOTAL_1H'
    FUT_SHORT_LIQ_USD_TOTAL_1H = 'FUT_SHORT_LIQ_USD_TOTAL_1H'
    OPT_ATM_IMPL_VOLATY_1_WEEK_1H = 'OPT_ATM_IMPL_VOLATY_1_WEEK_1H'
    OPT_VOL_DAILY_SUM_NATIVE_1H = 'OPT_VOL_DAILY_SUM_NATIVE_1H'
    OPT_VOL_DAILY_SUM_USD_1H = 'OPT_VOL_DAILY_SUM_USD_1H'
    OPT_VOL_PUT_CALL_RATIO_1H = 'OPT_VOL_PUT_CALL_RATIO_1H'
    PCT_VOL_IN_PROFIT_1H = 'PCT_VOL_IN_PROFIT_1H'
    R_HODL_RATIO_1H = 'R_HODL_RATIO_1H'
    FEAR_GREED_1D = 'FEAR_GREED_1D'
    SLRV_RATIO_1H = 'SLRV_RATIO_1H'
    SELL_SIDE_RISK_RATIO_1H = 'SELL_SIDE_RISK_RATIO_1H'
    DORMANCY_1H = 'DORMANCY_1H'
    MVRV_RATIO_1H = 'MVRV_RATIO_1H'
    THERMOCAP_1H = 'THERMOCAP_1H'
    BALANCE_EXCHANGES_NATIVE_1H = 'BALANCE_EXCHANGES_NATIVE_1H'
    BALANCE_EXCHANGES_USD_1H = 'BALANCE_EXCHANGES_USD_1H'
    EX_VOL_MOMENTUM_1H = 'EX_VOL_MOMENTUM_1H'
    SELLER_EXHAUSTION_CONSTANT_1D = 'SELLER_EXHAUSTION_CONSTANT_1D'
    STABLECOIN_SUPPLY_RATIO_1H = 'STABLECOIN_SUPPLY_RATIO_1H'
    LIFESPAN_CDD_MOMENTUM_1H = 'LIFESPAN_CDD_MOMENTUM_1H'
    LTH_NUPL_1H = 'LTH_NUPL_1H'
    STH_NUPL_1H = 'STH_NUPL_1H'
    REALIZED_CAP_BY_AGE_1H = 'REALIZED_CAP_BY_AGE_1H'
    SPENT_VOLUME_IN_LOSS_BY_AGE_NATIVE_1H = 'SPENT_VOLUME_IN_LOSS_BY_AGE_NATIVE_1H'
    SPENT_VOLUME_IN_LOSS_BY_AGE_USD_1H = 'SPENT_VOLUME_IN_LOSS_BY_AGE_USD_1H'
    INVESTOR_CAPITALIZATION_1H = 'INVESTOR_CAPITALIZATION_1H'
    ACCUMULATION_TREND_SCORE_1D = 'ACCUMULATION_TREND_SCORE_1D'
    SOPR_1H = "SOPR_1H"
    MARKET_PRICE_USD_CLOSE_1H = 'MARKET_PRICE_USD_CLOSE_1H'
    MARKET_PRICE_USD_OHLC_1H = 'MARKET_PRICE_USD_OHLC_1H'
    MARKET_CAP_USD_1H = 'MARKET_CAP_USD_1H'
    MARKET_CAP_REALIZED_USD_1H = 'MARKET_CAP_REALIZED_USD_1H'
    MARKET_MVRV_Z_SCORE_1H = 'MARKET_MVRV_Z_SCORE_1H'
    MARKET_PRICE_DRAWDOWN_RELATIVE_1H = 'MARKET_PRICE_DRAWDOWN_RELATIVE_1H'
    TX_COUNT_1H = 'TX_COUNT_1H'
    TX_RATE_1H = 'TX_RATE_1H'
    TX_TRANSFERS_VOL_SUM_NATIVE_1H = 'TX_TRANSFERS_VOL_SUM_NATIVE_1H'
    TX_TRANSFERS_VOL_SUM_USD_1H = 'TX_TRANSFERS_VOL_SUM_USD_1H'
    TX_TRANSFERS_VOL_MEAN_NATIVE_1H = 'TX_TRANSFERS_VOL_MEAN_NATIVE_1H'
    TX_TRANSFERS_VOL_MEAN_USD_1H = 'TX_TRANSFERS_VOL_MEAN_USD_1H'
    TX_TRANSFERS_VOL_MEDIAN_NATIVE_1H = 'TX_TRANSFERS_VOL_MEDIAN_NATIVE_1H'
    TX_TRANSFERS_VOL_MEDIAN_USD_1H = 'TX_TRANSFERS_VOL_MEDIAN_USD_1H'
    ADDR_ACTIVE_COUNT_1H = 'ADDR_ACTIVE_COUNT_1H'
    ADDR_COUNT_1H = 'ADDR_COUNT_1H'
    ADDR_NEW_NON_ZERO_COUNT_1H = 'ADDR_NEW_NON_ZERO_COUNT_1H'
    ADDR_SENDING_COUNT_1H = 'ADDR_SENDING_COUNT_1H'
    ADDR_RECEIVING_COUNT_1H = 'ADDR_RECEIVING_COUNT_1H'
    ADDR_NON_ZERO_COUNT_1H = 'ADDR_NON_ZERO_COUNT_1H'
    SUPPLY_CURRENT_NATIVE_1H = 'SUPPLY_CURRENT_NATIVE_1H'
    SUPPLY_CURRENT_USD_1H = 'SUPPLY_CURRENT_USD_1H'
    SUPPLY_PROFIT_RELATIVE_1H = 'SUPPLY_PROFIT_RELATIVE_1H'
    NET_REALIZED_PROFIT_LOSS_1H = 'NET_REALIZED_PROFIT_LOSS_1H'
    BALANCE_EXCHANGES_RELATIVE_1H = 'BALANCE_EXCHANGES_RELATIVE_1H'
    FUT_OPEN_INTEREST_SUM_NATIVE_1H = 'FUT_OPEN_INTEREST_SUM_NATIVE_1H'
    FUT_OPEN_INTEREST_SUM_USD_1H = 'FUT_OPEN_INTEREST_SUM_USD_1H'
    FUT_OPEN_INTEREST_PERP_SUM_NATIVE_1H = 'FUT_OPEN_INTEREST_PERP_SUM_NATIVE_1H'
    FUT_OPEN_INTEREST_PERP_SUM_USD_1H = 'FUT_OPEN_INTEREST_PERP_SUM_USD_1H'
    FUT_FUNDING_RATE_PERP_1H = 'FUT_FUNDING_RATE_PERP_1H'
    FUT_FUNDING_RATE_PERP_ALL_1H = 'FUT_FUNDING_RATE_PERP_ALL_1H'
    FUT_VOL_DAILY_SUM_NATIVE_1H = 'FUT_VOL_DAILY_SUM_NATIVE_1H'
    FUT_VOL_DAILY_SUM_USD_1H = 'FUT_VOL_DAILY_SUM_USD_1H'
    FUT_VOL_DAILY_PERP_SUM_NATIVE_1H = 'FUT_VOL_DAILY_PERP_SUM_NATIVE_1H'
    FUT_VOL_DAILY_PERP_SUM_USD_1H = 'FUT_VOL_DAILY_PERP_SUM_USD_1H'
    FUT_LIQ_VOL_LONG_RELATIVE_1H = 'FUT_LIQ_VOL_LONG_RELATIVE_1H'
    FUT_ANNUALIZED_BASIS_3M_1H = 'FUT_ANNUALIZED_BASIS_3M_1H'
    OPT_OPEN_INTEREST_SUM_NATIVE_1H = 'OPT_OPEN_INTEREST_SUM_NATIVE_1H'
    OPT_OPEN_INTEREST_SUM_USD_1H = 'OPT_OPEN_INTEREST_SUM_USD_1H'
    FEES_VOL_SUM_NATIVE_1H = 'FEES_VOL_SUM_NATIVE_1H'
    FEES_VOL_SUM_USD_1H = 'FEES_VOL_SUM_USD_1H'
    FEES_VOL_MEAN_NATIVE_1H = 'FEES_VOL_MEAN_NATIVE_1H'
    FEES_VOL_MEAN_USD_1H = 'FEES_VOL_MEAN_USD_1H'
    FEES_VOL_MEDIAN_NATIVE_1H = 'FEES_VOL_MEDIAN_NATIVE_1H'
    FEES_VOL_MEDIAN_USD_1H = 'FEES_VOL_MEDIAN_USD_1H'
    BTC_DOMINANCE_1D = 'BTC_DOMINANCE_1D'
    EVENT_1H = 'EVENT_1H'

    def get_period_in_mill(self) -> int:
        if self in [DataType.KLINE_1H,
                    DataType.INDEX_PRICE_1H,
                    DataType.MARK_PRICE_1H,
                    DataType.PREMIUM_INDEX_1H,
                    DataType.OPEN_INTEREST_1H,
                    DataType.INTEREST_RATE,
                    DataType.HAIRCUT,
                    DataType.HAIRCUT_DE,
                    DataType.PM_COLLATERAL_RATIO,
                    DataType.MMR,
                    DataType.MMD,
                    DataType.OPTIONS_25DELTA_SKEW_1H,
                    DataType.FUT_EST_LEVG_RATIO_1H,
                    DataType.CASH_MARG_FUT_OPEN_INTEREST_NATIVE_1H,
                    DataType.CASH_MARG_FUT_OPEN_INTEREST_USD_1H,
                    DataType.FUT_LONG_LIQ_NATIVE_TOTAL_1H,
                    DataType.FUT_SHORT_LIQ_NATIVE_TOTAL_1H,
                    DataType.FUT_LONG_LIQ_USD_TOTAL_1H,
                    DataType.FUT_SHORT_LIQ_USD_TOTAL_1H,
                    DataType.OPT_ATM_IMPL_VOLATY_1_WEEK_1H,
                    DataType.OPT_VOL_DAILY_SUM_NATIVE_1H,
                    DataType.OPT_VOL_DAILY_SUM_USD_1H,
                    DataType.OPT_VOL_PUT_CALL_RATIO_1H,
                    DataType.R_HODL_RATIO_1H,
                    DataType.PCT_VOL_IN_PROFIT_1H,
                    DataType.SLRV_RATIO_1H,
                    DataType.SELL_SIDE_RISK_RATIO_1H,
                    DataType.DORMANCY_1H,
                    DataType.MVRV_RATIO_1H,
                    DataType.THERMOCAP_1H,
                    DataType.BALANCE_EXCHANGES_NATIVE_1H,
                    DataType.BALANCE_EXCHANGES_USD_1H,
                    DataType.EX_VOL_MOMENTUM_1H,
                    DataType.STABLECOIN_SUPPLY_RATIO_1H,
                    DataType.LIFESPAN_CDD_MOMENTUM_1H,
                    DataType.LTH_NUPL_1H,
                    DataType.STH_NUPL_1H,
                    DataType.REALIZED_CAP_BY_AGE_1H,
                    DataType.SPENT_VOLUME_IN_LOSS_BY_AGE_NATIVE_1H,
                    DataType.SPENT_VOLUME_IN_LOSS_BY_AGE_USD_1H,
                    DataType.INVESTOR_CAPITALIZATION_1H,
                    DataType.SOPR_1H,
                    DataType.MARKET_PRICE_USD_CLOSE_1H,
                    DataType.MARKET_PRICE_USD_OHLC_1H,
                    DataType.MARKET_CAP_USD_1H,
                    DataType.MARKET_CAP_REALIZED_USD_1H,
                    DataType.MARKET_MVRV_Z_SCORE_1H,
                    DataType.MARKET_PRICE_DRAWDOWN_RELATIVE_1H,
                    DataType.TX_COUNT_1H,
                    DataType.TX_RATE_1H,
                    DataType.TX_TRANSFERS_VOL_SUM_NATIVE_1H,
                    DataType.TX_TRANSFERS_VOL_SUM_USD_1H,
                    DataType.TX_TRANSFERS_VOL_MEAN_NATIVE_1H,
                    DataType.TX_TRANSFERS_VOL_MEAN_USD_1H,
                    DataType.TX_TRANSFERS_VOL_MEDIAN_NATIVE_1H,
                    DataType.TX_TRANSFERS_VOL_MEDIAN_USD_1H,
                    DataType.ADDR_ACTIVE_COUNT_1H,
                    DataType.ADDR_COUNT_1H,
                    DataType.ADDR_NEW_NON_ZERO_COUNT_1H,
                    DataType.ADDR_SENDING_COUNT_1H,
                    DataType.ADDR_RECEIVING_COUNT_1H,
                    DataType.ADDR_NON_ZERO_COUNT_1H,
                    DataType.SUPPLY_CURRENT_NATIVE_1H,
                    DataType.SUPPLY_CURRENT_USD_1H,
                    DataType.SUPPLY_PROFIT_RELATIVE_1H,
                    DataType.NET_REALIZED_PROFIT_LOSS_1H,
                    DataType.BALANCE_EXCHANGES_RELATIVE_1H,
                    DataType.FUT_OPEN_INTEREST_SUM_NATIVE_1H,
                    DataType.FUT_OPEN_INTEREST_SUM_USD_1H,
                    DataType.FUT_OPEN_INTEREST_PERP_SUM_NATIVE_1H,
                    DataType.FUT_OPEN_INTEREST_PERP_SUM_USD_1H,
                    DataType.FUT_FUNDING_RATE_PERP_1H,
                    DataType.FUT_FUNDING_RATE_PERP_ALL_1H,
                    DataType.FUT_VOL_DAILY_SUM_NATIVE_1H,
                    DataType.FUT_VOL_DAILY_SUM_USD_1H,
                    DataType.FUT_VOL_DAILY_PERP_SUM_NATIVE_1H,
                    DataType.FUT_VOL_DAILY_PERP_SUM_USD_1H,
                    DataType.FUT_LIQ_VOL_LONG_RELATIVE_1H,
                    DataType.FUT_ANNUALIZED_BASIS_3M_1H,
                    DataType.OPT_OPEN_INTEREST_SUM_NATIVE_1H,
                    DataType.OPT_OPEN_INTEREST_SUM_USD_1H,
                    DataType.FEES_VOL_SUM_NATIVE_1H,
                    DataType.FEES_VOL_SUM_USD_1H,
                    DataType.FEES_VOL_MEAN_NATIVE_1H,
                    DataType.FEES_VOL_MEAN_USD_1H,
                    DataType.FEES_VOL_MEDIAN_NATIVE_1H,
                    DataType.FEES_VOL_MEDIAN_USD_1H,
                    DataType.EVENT_1H]:
            return 3600000
        elif self in [DataType.KLINE_2H,
                      DataType.INDEX_PRICE_2H,
                      DataType.MARK_PRICE_2H,
                      DataType.PREMIUM_INDEX_2H]:
            return 7200000
        elif self in [DataType.KLINE_4H,
                      DataType.INDEX_PRICE_4H,
                      DataType.MARK_PRICE_4H,
                      DataType.PREMIUM_INDEX_4H]:
            return 14400000
        elif self in [DataType.KLINE_8H,
                      DataType.INDEX_PRICE_8H,
                      DataType.MARK_PRICE_8H,
                      DataType.PREMIUM_INDEX_8H]:
            return 28800000
        elif self in [DataType.KLINE_12H,
                      DataType.INDEX_PRICE_12H,
                      DataType.MARK_PRICE_12H,
                      DataType.PREMIUM_INDEX_12H]:
            return 43200000
        elif self in [DataType.KLINE_1D,
                      DataType.INDEX_PRICE_1D,
                      DataType.MARK_PRICE_1D,
                      DataType.PREMIUM_INDEX_1D,
                      DataType.OPTIONS_25DELTA_SKEW_24H,
                      DataType.FEAR_GREED_1D,
                      DataType.SELLER_EXHAUSTION_CONSTANT_1D,
                      DataType.STAKING_RATE,
                      DataType.ACCUMULATION_TREND_SCORE_1D,
                      DataType.BTC_DOMINANCE_1D]:
            return 86400000
        elif self in [DataType.KLINE_1M,
                      DataType.INDEX_PRICE_1M,
                      DataType.MARK_PRICE_1M,
                      DataType.PREMIUM_INDEX_1M,
                      DataType.INSURANCE_FUND]:
            return 60000
        elif self in [DataType.KLINE_3M,
                      DataType.INDEX_PRICE_3M,
                      DataType.MARK_PRICE_3M,
                      DataType.PREMIUM_INDEX_3M]:
            return 180000
        elif self in [DataType.KLINE_5M,
                      DataType.INDEX_PRICE_5M,
                      DataType.MARK_PRICE_5M,
                      DataType.PREMIUM_INDEX_5M]:
            return 300000
        elif self in [DataType.OPTIONS_25DELTA_SKEW_10M,
                      DataType.FUNDING_RATE_10M]:
            return 600000
        elif self in [DataType.KLINE_15M,
                      DataType.INDEX_PRICE_15M,
                      DataType.MARK_PRICE_15M,
                      DataType.PREMIUM_INDEX_15M]:
            return 900000
        elif self in [DataType.KLINE_30M,
                      DataType.INDEX_PRICE_30M,
                      DataType.MARK_PRICE_30M,
                      DataType.PREMIUM_INDEX_30M]:
            return 1800000
        raise ParamInvalidError('Cannot get period from data type')

    def is_kline_data(self) -> bool:
        return self.name.split('_', 1)[0] == 'KLINE'

    def is_index_price_data(self) -> bool:
        return self.name.startswith('INDEX_PRICE')

    def is_mark_price_data(self) -> bool:
        return self.name.startswith('MARK_PRICE')

    def is_premium_index_data(self) -> bool:
        return self.name.startswith('PREMIUM_INDEX')

    def is_funding_rate_data(self) -> bool:
        return self.name.startswith('FUNDING_RATE')

    def is_interest_rate_data(self) -> bool:
        return self == DataType.INTEREST_RATE

    def is_open_interest_data(self) -> bool:
        return self.name.rsplit('_', 1)[0] == 'OPEN_INTEREST'

    def is_haircut_data(self) -> bool:
        return self == DataType.HAIRCUT

    def is_haircut_de_data(self) -> bool:
        return self == DataType.HAIRCUT_DE

    def is_pm_collateral_ratio_data(self) -> bool:
        return self == DataType.PM_COLLATERAL_RATIO

    def is_mmr_data(self) -> bool:
        return self == DataType.MMR

    def is_mmd_data(self) -> bool:
        return self == DataType.MMD

    def is_staking_rate_data(self) -> bool:
        return self == DataType.STAKING_RATE

    def is_insurance_fund_data(self) -> bool:
        return self == DataType.INSURANCE_FUND

    def is_event_data(self) -> bool:
        return self.name.startswith('EVENT_')

    def is_options_25delta_skew_data(self) -> bool:
        return self.name.startswith('OPTIONS_25DELTA_SKEW')

    def is_glass_node_data(self) -> bool:
        return self in [DataType.FUT_EST_LEVG_RATIO_1H,
                        DataType.CASH_MARG_FUT_OPEN_INTEREST_NATIVE_1H,
                        DataType.CASH_MARG_FUT_OPEN_INTEREST_USD_1H,
                        DataType.FUT_LONG_LIQ_NATIVE_TOTAL_1H,
                        DataType.FUT_SHORT_LIQ_NATIVE_TOTAL_1H,
                        DataType.FUT_LONG_LIQ_USD_TOTAL_1H,
                        DataType.FUT_SHORT_LIQ_USD_TOTAL_1H,
                        DataType.OPT_ATM_IMPL_VOLATY_1_WEEK_1H,
                        DataType.OPT_VOL_DAILY_SUM_NATIVE_1H,
                        DataType.OPT_VOL_DAILY_SUM_USD_1H,
                        DataType.OPT_VOL_PUT_CALL_RATIO_1H,
                        DataType.R_HODL_RATIO_1H,
                        DataType.PCT_VOL_IN_PROFIT_1H,
                        DataType.SLRV_RATIO_1H,
                        DataType.SELL_SIDE_RISK_RATIO_1H,
                        DataType.DORMANCY_1H,
                        DataType.MVRV_RATIO_1H,
                        DataType.THERMOCAP_1H,
                        DataType.BALANCE_EXCHANGES_NATIVE_1H,
                        DataType.BALANCE_EXCHANGES_USD_1H,
                        DataType.EX_VOL_MOMENTUM_1H,
                        DataType.STABLECOIN_SUPPLY_RATIO_1H,
                        DataType.LIFESPAN_CDD_MOMENTUM_1H,
                        DataType.LTH_NUPL_1H,
                        DataType.STH_NUPL_1H,
                        DataType.FEAR_GREED_1D,
                        DataType.SELLER_EXHAUSTION_CONSTANT_1D,
                        DataType.REALIZED_CAP_BY_AGE_1H,
                        DataType.SPENT_VOLUME_IN_LOSS_BY_AGE_NATIVE_1H,
                        DataType.SPENT_VOLUME_IN_LOSS_BY_AGE_USD_1H,
                        DataType.INVESTOR_CAPITALIZATION_1H,
                        DataType.ACCUMULATION_TREND_SCORE_1D,
                        DataType.SOPR_1H,
                        DataType.MARKET_PRICE_USD_CLOSE_1H,
                        DataType.MARKET_PRICE_USD_OHLC_1H,
                        DataType.MARKET_CAP_USD_1H,
                        DataType.MARKET_CAP_REALIZED_USD_1H,
                        DataType.MARKET_MVRV_Z_SCORE_1H,
                        DataType.MARKET_PRICE_DRAWDOWN_RELATIVE_1H,
                        DataType.TX_COUNT_1H,
                        DataType.TX_RATE_1H,
                        DataType.TX_TRANSFERS_VOL_SUM_NATIVE_1H,
                        DataType.TX_TRANSFERS_VOL_SUM_USD_1H,
                        DataType.TX_TRANSFERS_VOL_MEAN_NATIVE_1H,
                        DataType.TX_TRANSFERS_VOL_MEAN_USD_1H,
                        DataType.TX_TRANSFERS_VOL_MEDIAN_NATIVE_1H,
                        DataType.TX_TRANSFERS_VOL_MEDIAN_USD_1H,
                        DataType.ADDR_ACTIVE_COUNT_1H,
                        DataType.ADDR_COUNT_1H,
                        DataType.ADDR_NEW_NON_ZERO_COUNT_1H,
                        DataType.ADDR_SENDING_COUNT_1H,
                        DataType.ADDR_RECEIVING_COUNT_1H,
                        DataType.ADDR_NON_ZERO_COUNT_1H,
                        DataType.SUPPLY_CURRENT_NATIVE_1H,
                        DataType.SUPPLY_CURRENT_USD_1H,
                        DataType.SUPPLY_PROFIT_RELATIVE_1H,
                        DataType.NET_REALIZED_PROFIT_LOSS_1H,
                        DataType.BALANCE_EXCHANGES_RELATIVE_1H,
                        DataType.FUT_OPEN_INTEREST_SUM_NATIVE_1H,
                        DataType.FUT_OPEN_INTEREST_SUM_USD_1H,
                        DataType.FUT_OPEN_INTEREST_PERP_SUM_NATIVE_1H,
                        DataType.FUT_OPEN_INTEREST_PERP_SUM_USD_1H,
                        DataType.FUT_FUNDING_RATE_PERP_1H,
                        DataType.FUT_FUNDING_RATE_PERP_ALL_1H,
                        DataType.FUT_VOL_DAILY_SUM_NATIVE_1H,
                        DataType.FUT_VOL_DAILY_SUM_USD_1H,
                        DataType.FUT_VOL_DAILY_PERP_SUM_NATIVE_1H,
                        DataType.FUT_VOL_DAILY_PERP_SUM_USD_1H,
                        DataType.FUT_LIQ_VOL_LONG_RELATIVE_1H,
                        DataType.FUT_ANNUALIZED_BASIS_3M_1H,
                        DataType.OPT_OPEN_INTEREST_SUM_NATIVE_1H,
                        DataType.OPT_OPEN_INTEREST_SUM_USD_1H,
                        DataType.FEES_VOL_SUM_NATIVE_1H,
                        DataType.FEES_VOL_SUM_USD_1H,
                        DataType.FEES_VOL_MEAN_NATIVE_1H,
                        DataType.FEES_VOL_MEAN_USD_1H,
                        DataType.FEES_VOL_MEDIAN_NATIVE_1H,
                        DataType.FEES_VOL_MEDIAN_USD_1H,
                        DataType.BTC_DOMINANCE_1D]

    def is_glass_node_single_value_data(self) -> bool:
        return self in [DataType.FUT_EST_LEVG_RATIO_1H,
                        DataType.CASH_MARG_FUT_OPEN_INTEREST_NATIVE_1H,
                        DataType.CASH_MARG_FUT_OPEN_INTEREST_USD_1H,
                        DataType.FUT_LONG_LIQ_NATIVE_TOTAL_1H,
                        DataType.FUT_SHORT_LIQ_NATIVE_TOTAL_1H,
                        DataType.FUT_LONG_LIQ_USD_TOTAL_1H,
                        DataType.FUT_SHORT_LIQ_USD_TOTAL_1H,
                        DataType.OPT_ATM_IMPL_VOLATY_1_WEEK_1H,
                        DataType.OPT_VOL_DAILY_SUM_NATIVE_1H,
                        DataType.OPT_VOL_DAILY_SUM_USD_1H,
                        DataType.OPT_VOL_PUT_CALL_RATIO_1H,
                        DataType.R_HODL_RATIO_1H,
                        DataType.PCT_VOL_IN_PROFIT_1H,
                        DataType.SLRV_RATIO_1H,
                        DataType.SELL_SIDE_RISK_RATIO_1H,
                        DataType.DORMANCY_1H,
                        DataType.MVRV_RATIO_1H,
                        DataType.THERMOCAP_1H,
                        DataType.BALANCE_EXCHANGES_NATIVE_1H,
                        DataType.BALANCE_EXCHANGES_USD_1H,
                        DataType.EX_VOL_MOMENTUM_1H,
                        DataType.LIFESPAN_CDD_MOMENTUM_1H,
                        DataType.LTH_NUPL_1H,
                        DataType.STH_NUPL_1H,
                        DataType.FEAR_GREED_1D,
                        DataType.SELLER_EXHAUSTION_CONSTANT_1D,
                        DataType.INVESTOR_CAPITALIZATION_1H,
                        DataType.SOPR_1H,
                        DataType.MARKET_PRICE_USD_CLOSE_1H,
                        DataType.MARKET_CAP_USD_1H,
                        DataType.MARKET_CAP_REALIZED_USD_1H,
                        DataType.MARKET_MVRV_Z_SCORE_1H,
                        DataType.MARKET_PRICE_DRAWDOWN_RELATIVE_1H,
                        DataType.TX_COUNT_1H,
                        DataType.TX_RATE_1H,
                        DataType.TX_TRANSFERS_VOL_SUM_NATIVE_1H,
                        DataType.TX_TRANSFERS_VOL_SUM_USD_1H,
                        DataType.TX_TRANSFERS_VOL_MEAN_NATIVE_1H,
                        DataType.TX_TRANSFERS_VOL_MEAN_USD_1H,
                        DataType.TX_TRANSFERS_VOL_MEDIAN_NATIVE_1H,
                        DataType.TX_TRANSFERS_VOL_MEDIAN_USD_1H,
                        DataType.ADDR_ACTIVE_COUNT_1H,
                        DataType.ADDR_COUNT_1H,
                        DataType.ADDR_NEW_NON_ZERO_COUNT_1H,
                        DataType.ADDR_SENDING_COUNT_1H,
                        DataType.ADDR_RECEIVING_COUNT_1H,
                        DataType.ADDR_NON_ZERO_COUNT_1H,
                        DataType.SUPPLY_CURRENT_NATIVE_1H,
                        DataType.SUPPLY_CURRENT_USD_1H,
                        DataType.SUPPLY_PROFIT_RELATIVE_1H,
                        DataType.NET_REALIZED_PROFIT_LOSS_1H,
                        DataType.BALANCE_EXCHANGES_RELATIVE_1H,
                        DataType.FUT_OPEN_INTEREST_SUM_NATIVE_1H,
                        DataType.FUT_OPEN_INTEREST_SUM_USD_1H,
                        DataType.FUT_OPEN_INTEREST_PERP_SUM_NATIVE_1H,
                        DataType.FUT_OPEN_INTEREST_PERP_SUM_USD_1H,
                        DataType.FUT_FUNDING_RATE_PERP_1H,
                        DataType.FUT_VOL_DAILY_SUM_NATIVE_1H,
                        DataType.FUT_VOL_DAILY_SUM_USD_1H,
                        DataType.FUT_VOL_DAILY_PERP_SUM_NATIVE_1H,
                        DataType.FUT_VOL_DAILY_PERP_SUM_USD_1H,
                        DataType.FUT_LIQ_VOL_LONG_RELATIVE_1H,
                        DataType.FUT_ANNUALIZED_BASIS_3M_1H,
                        DataType.OPT_OPEN_INTEREST_SUM_NATIVE_1H,
                        DataType.OPT_OPEN_INTEREST_SUM_USD_1H,
                        DataType.FEES_VOL_SUM_NATIVE_1H,
                        DataType.FEES_VOL_SUM_USD_1H,
                        DataType.FEES_VOL_MEAN_NATIVE_1H,
                        DataType.FEES_VOL_MEAN_USD_1H,
                        DataType.FEES_VOL_MEDIAN_NATIVE_1H,
                        DataType.FEES_VOL_MEDIAN_USD_1H,
                        DataType.BTC_DOMINANCE_1D]

    def is_stablecoin_supply_ratio_data(self) -> bool:
        return self == DataType.STABLECOIN_SUPPLY_RATIO_1H

    def is_glass_node_map_data(self) -> bool:
        return self in [DataType.REALIZED_CAP_BY_AGE_1H,
                        DataType.SPENT_VOLUME_IN_LOSS_BY_AGE_NATIVE_1H,
                        DataType.SPENT_VOLUME_IN_LOSS_BY_AGE_USD_1H,
                        DataType.ACCUMULATION_TREND_SCORE_1D,
                        DataType.MARKET_PRICE_USD_OHLC_1H,
                        DataType.FUT_FUNDING_RATE_PERP_ALL_1H]

    def is_market_data(self) -> bool:
        return (self.is_kline_data()
                or self.is_funding_rate_data()
                or self.is_interest_rate_data()
                or self.is_open_interest_data()
                or self.is_haircut_data()
                or self.is_haircut_de_data()
                or self.is_pm_collateral_ratio_data()
                or self.is_mmr_data()
                or self.is_mmd_data()
                or self.is_staking_rate_data()
                or self.is_insurance_fund_data()
                or self.is_index_price_data()
                or self.is_mark_price_data()
                or self.is_premium_index_data()
                or self.is_options_25delta_skew_data()
                or self.is_glass_node_data()
                or self.is_event_data())

    def is_countable(self) -> bool:
        if (self.is_funding_rate_data()
                or self.is_interest_rate_data()
                or self.is_open_interest_data()
                or self.is_haircut_data()
                or self.is_haircut_de_data()
                or self.is_pm_collateral_ratio_data()
                or self.is_mmr_data()
                or self.is_mmd_data()
                or self.is_staking_rate_data()
                or self.is_insurance_fund_data()
                or self.is_options_25delta_skew_data()
                or self.is_glass_node_data()
                or self.is_event_data()
                or self == DataType.NOTEBOOK
                or self == DataType.STREAMING
                or self == DataType.SEQUENCED):
            return False
        return True

    @staticmethod
    def is_notebook(data_type: str) -> bool:
        return DataType.NOTEBOOK.name == data_type

    @staticmethod
    def validate(data_type: str) -> bool:
        return data_type in [member.name for member in DataType]


class FileType(Enum):
    CSV = 'CSV'
    GZIP = 'GZIP'
    NOTEBOOK = 'NOTEBOOK'


class DecimalStorageType(Enum):
    FLOAT = 'FLOAT'
    DECIMAL = 'DECIMAL'
    STRING = 'STRING'
