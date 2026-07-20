from datetime import datetime, timezone

from nexus_data_hub_sdk.share.constants import Constants


class DateTimeHelper:
    @staticmethod
    def now_epoch_milliseconds():
        return int(
            datetime.timestamp(
                datetime.now(
                    tz=timezone.utc)) *
            Constants.ONE_SECOND_IN_MILLI)
