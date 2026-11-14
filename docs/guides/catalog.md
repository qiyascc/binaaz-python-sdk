# Catalog

The catalog is the reference data a listing points at: categories, cities, regions (districts), townships (settlements) and landmarks such as metro stations. It is public, so the calls work on a client with no session:

```python
from binaaz_sdk import BinaAz

with BinaAz() as bina:
    cities = bina.catalog.cities()
```

Catalog calls are reads, so they are retried with backoff when the network or bina.az has a hiccup.

## Categories

```python
for node in bina.catalog.categories():
    print(node.id, node.name)
    for child in node.children:
        print("    ", child.id, child.name)
```

Each item is a {py:class}`~binaaz_sdk.CategoryNode` with `id`, `name` and `children` (a tuple of `Place` with `id` and `name`). The names are the ones bina.az shows. The {py:class}`~binaaz_sdk.Category` enum holds the ids of the common categories for `Listing.category_id`; this call is the live list, useful when bina.az adds a new one.

## Cities

```python
cities = bina.catalog.cities()
by_name = {city.name: city.id for city in cities}
```

Each item is a {py:class}`~binaaz_sdk.Place` with `id` and `name`. Put the id in `Listing.location.city_id`.

## Regions

Regions are the districts of a city:

```python
regions = bina.catalog.regions("1")
```

Put the id in `location.region_id`.

## Townships

Townships are the settlements inside a region:

```python
townships = bina.catalog.townships("4")
```

Put the id in `location.township_id`.

## Landmarks

Landmarks are the named places near a point on the map, metro stations among them. bina.az picks them by city and coordinates:

```python
landmarks = bina.catalog.landmarks("1", 40.379, 49.846)
for place in landmarks:
    print(place.id, place.name)
```

Put the ids you want in `location.landmark_ids`.

## A full location

Putting it together, with names chosen in code:

```python
def find(places, name):
    return next(place for place in places if place.name == name)

city = find(bina.catalog.cities(), "Bakı")
region = find(bina.catalog.regions(city.id), "Yasamal r.")
lat, lng = 40.393, 49.808
landmarks = bina.catalog.landmarks(city.id, lat, lng)

location = {
    "address": "Şərifzadə küçəsi 10",
    "city_id": city.id,
    "region_id": region.id,
    "latitude": lat,
    "longitude": lng,
    "landmark_ids": [landmarks[0].id] if landmarks else None,
}
```

The exact spelling of names is whatever bina.az returns; print the lists once to see them.

## Cache the catalog

Cities, regions and townships rarely change. If you post many listings, read them once and keep them in memory or in a file rather than calling the catalog for every listing:

```python
import json
from pathlib import Path

CACHE = Path("binaaz-cities.json")

if CACHE.exists():
    cities = json.loads(CACHE.read_text())
else:
    cities = {place.name: place.id for place in bina.catalog.cities()}
    CACHE.write_text(json.dumps(cities, ensure_ascii=False))
```

## Ids

All catalog ids are strings. An id containing `/`, `?`, `#`, `&` or a space, or one longer than 64 characters, is refused with `InvalidRequestError` before a request is made.
