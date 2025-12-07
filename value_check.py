from datetime import datetime, timezone, timedelta
from nook.common.date_utils import target_dates_set

print(f"System Time (UTC?): {datetime.now()}")
print(f"Target Dates (JST): {target_dates_set(1)}")

ts = datetime.now(timezone.utc).timestamp()
local_date_from_system = datetime.fromtimestamp(ts).date()
print(f"Local Date from TS: {local_date_from_system}")

print(f"Match? {local_date_from_system in target_dates_set(1)}")
