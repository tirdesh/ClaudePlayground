# Food Log

Log meals to Google Health from a Claude session. Calories and protein come from [menu.md](menu.md); estimate fat and carbs.

## Credentials

Set as environment variables in the cloud environment settings, never in this repo:

- `GOOGLE_HEALTH_CLIENT_ID`
- `GOOGLE_HEALTH_CLIENT_SECRET`
- `GOOGLE_HEALTH_REFRESH_TOKEN`

The OAuth app is in Testing mode, so the refresh token lasts 7 days. To get a new one, set the redirect URI to `http://localhost`, open the URL below, and exchange the returned `code` at `https://oauth2.googleapis.com/token` (`grant_type=authorization_code`, `redirect_uri=http://localhost`).

```
https://accounts.google.com/o/oauth2/v2/auth?client_id=$GOOGLE_HEALTH_CLIENT_ID&redirect_uri=http://localhost&response_type=code&scope=https://www.googleapis.com/auth/googlehealth.nutrition.writeonly%20https://www.googleapis.com/auth/googlehealth.nutrition.readonly&access_type=offline&prompt=consent
```

## Get an access token

```sh
curl -sS https://oauth2.googleapis.com/token \
  -d client_id="$GOOGLE_HEALTH_CLIENT_ID" \
  -d client_secret="$GOOGLE_HEALTH_CLIENT_SECRET" \
  -d refresh_token="$GOOGLE_HEALTH_REFRESH_TOKEN" \
  -d grant_type=refresh_token
```

## API (Google Health v4)

Base: `https://health.googleapis.com/v4/users/me/dataTypes/nutrition-log/dataPoints`

Create (POST to base). Times are UTC; the user is in America/New_York, so `startUtcOffset` is `-18000s` in EST and `-14400s` in EDT.

```json
{
  "nutritionLog": {
    "interval": {
      "startTime": "2026-11-13T20:00:00Z", "startUtcOffset": "-18000s",
      "endTime": "2026-11-13T20:15:00Z", "endUtcOffset": "-18000s"
    },
    "mealType": "LUNCH",
    "foodDisplayName": "Rice + egg curry",
    "energy": {"kcal": 545},
    "totalFat": {"grams": 20},
    "totalCarbohydrate": {"grams": 70},
    "nutrients": [{"nutrient": "PROTEIN", "quantity": {"grams": 18}}]
  }
}
```

`mealType`: `BREAKFAST`, `LUNCH`, `DINNER`, `SNACK`.

List a day (GET base):

```
filter=nutrition_log.interval.civil_start_time >= "2026-11-13" AND nutrition_log.interval.civil_start_time < "2026-11-14"
```

Delete: POST `{base}:batchDelete` with `{"names": ["users/.../dataPoints/<id>"]}`.

PATCH cannot change an entry's time; to move an entry, create a new one and delete the old.

The API schema is at `https://health.googleapis.com/$discovery/rest?version=v4`.
