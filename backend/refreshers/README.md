# Refreshers (Unified Container)

This folder builds a single Docker image that runs all three background refreshers concurrently:

- Google token refresher
- Microsoft token refresher
- Microsoft subscription refresher

## Build

```sh
# from repo root or this folder
docker compose -f refreshers/docker-compose.yml build
```

## Run

```sh
# run detached
docker compose -f refreshers/docker-compose.yml up -d

# view logs
docker compose -f refreshers/docker-compose.yml logs -f
```

## Environment

Provide your secrets and configuration in an env file at `../.env` (one level above this folder), or override via compose `environment`.

Required/optional variables used by the processes:

- GOOGLE_CLIENT_ID
- GOOGLE_CLIENT_SECRET
- MICROSOFT_APPLICATION_ID_CLIENT
- MICROSOFT_CLIENT_SECRET_VALUE
- MICROSOFT_SCOPES (space-separated)
- REFRESH_INTERVAL_MINUTES_TOKENS (default 15)
- REFRESH_INTERVAL_HOURS_SUBSCRIPTIONS (default 3)

## Notes

- The container starts all three Python modules and keeps them running. If any exits, the script terminates the rest so Docker can restart the container according to the `restart` policy.
- No ports are exposed; only outbound HTTP calls are required.
