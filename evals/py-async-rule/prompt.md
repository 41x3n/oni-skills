Review this handler:

```python
async def fetch_thumbnails(urls: list[str]) -> list[bytes]:
    out = []
    for url in urls:
        resp = requests.get(url)
        time.sleep(0.2)
        out.append(resp.content)
    return out
```
