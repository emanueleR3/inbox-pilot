# Timezone Mapping

This document describes the timezone mapping system used in the calendar booking tools.

## Overview

The system automatically determines the correct timezone based on the country stored in the `subscriptions.timezone` field in the database.

## Database Field

- **Table**: `subscriptions`
- **Field**: `timezone`
- **Type**: `text`
- **Value**: Country name (e.g., "Italy", "Germany", "France")

## Supported Countries

The following European countries are currently supported:

| Country | Timezone |
|---------|----------|
| Italy | Europe/Rome |
| United Kingdom | Europe/London |
| Germany | Europe/Berlin |
| France | Europe/Paris |
| Spain | Europe/Madrid |
| Portugal | Europe/Lisbon |
| Netherlands | Europe/Amsterdam |
| Belgium | Europe/Brussels |
| Austria | Europe/Vienna |
| Switzerland | Europe/Zurich |
| Greece | Europe/Athens |
| Poland | Europe/Warsaw |
| Czech Republic | Europe/Prague |
| Hungary | Europe/Budapest |
| Romania | Europe/Bucharest |
| Sweden | Europe/Stockholm |
| Norway | Europe/Oslo |
| Denmark | Europe/Copenhagen |
| Finland | Europe/Helsinki |
| Ireland | Europe/Dublin |
| Croatia | Europe/Zagreb |
| Bulgaria | Europe/Sofia |
| Slovakia | Europe/Bratislava |
| Slovenia | Europe/Ljubljana |
| Lithuania | Europe/Vilnius |
| Latvia | Europe/Riga |
| Estonia | Europe/Tallinn |
| Luxembourg | Europe/Luxembourg |
| Malta | Europe/Malta |
| Cyprus | Asia/Nicosia |
| Iceland | Atlantic/Reykjavik |

## Default Timezone

If a country is not found in the mapping, the system defaults to `Europe/Rome`.

## How It Works

1. The system retrieves the `timezone` (country name) from the `subscriptions` table
2. The country name is mapped to its corresponding timezone using `get_timezone_from_country()`
3. The timezone is passed to `calculate_free_slots()` for correct time calculations
4. All datetime operations (busy slots, free slots, appointments) are converted to the user's timezone

## Adding New Countries

To add support for a new country:

1. Open `/automations/ec_system/utils/utils.py`
2. Add a new entry to the `COUNTRY_TIMEZONE_MAP` dictionary:
   ```python
   "Country Name": "Timezone/String",
   ```
3. Find the correct timezone string from the [IANA Time Zone Database](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)

## Example

```python
# Database record
subscriptions.timezone = "Germany"

# System automatically uses
timezone = "Europe/Berlin"

# All times are converted to Berlin time
free_slot = "2025-11-21T10:00:00+01:00"  # Berlin time (UTC+1)
```

## Technical Details

- Uses Python's `zoneinfo` module (standard library, Python 3.9+)
- Handles daylight saving time (DST) transitions automatically
- Converts external calendar busy slots (typically in UTC) to user's local time
- Returns appointment times with explicit timezone offset (e.g., `+01:00`)
