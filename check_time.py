from datetime import datetime, timezone
import MetaTrader5 as mt5

mt5.initialize()
now = datetime.now(timezone.utc)
print(f"UTC: {now.strftime('%H:%M')}")
ny_hour = (now.hour - 5) % 24
print(f"NY approx: {ny_hour}:{now.strftime('%M')}")
print(f"Day: {now.strftime('%A')}")
# ICT Killzones in UTC
killzones = {
    "London Open": (7, 10),  # 2-5 AM NY = 7-10 UTC
    "NY Open": (12, 15),  # 7-10 AM NY = 12-15 UTC
    "NY PM": (18, 21),  # 1-4 PM NY = 18-21 UTC
}
active = [k for k, v in killzones.items() if v[0] <= now.hour < v[1]]
print(f"Active killzone: {active if active else 'NONE'}")
print(
    f"Next killzone: NY PM at 18:00 UTC ({18 - now.hour}h {60 - now.minute}m away)"
    if not active and now.hour < 18
    else ""
)
mt5.shutdown()
