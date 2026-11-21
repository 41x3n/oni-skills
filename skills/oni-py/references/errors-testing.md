# Python errors and tests

## Own your exception hierarchy

```python
class VosError(Exception):
    """Base for everything this package raises."""

class NotFound(VosError):
    def __init__(self, kind: str, ident: str) -> None:
        super().__init__(f"{kind} {ident} not found")
        self.kind, self.ident = kind, ident

class Transient(VosError):
    """Retrying may succeed."""
```

One package-level base means a caller can write `except VosError` and be sure it catches your failures and not a `TypeError` from its own bug. Carry the data as attributes, not only inside the message — the handler needs `e.ident`, not a regex over `str(e)`.

Retryability is a *type*, not a guess at the call site. If `Transient` is in the hierarchy, the retry decorator needs no knowledge of the domain.

## Catch narrow, and the except body must do something

```python
try:
    meta = probe(path)
except FFProbeError as e:
    logger.warning("probe failed, using defaults", extra={"path": str(path), "err": str(e)})
    meta = Meta.default()
```

The three broad-catch forms that cause outages:

```python
except Exception:
    pass                 # corrupt state, no signal, nothing to debug
except Exception as e:
    logger.error(e)      # loses the traceback; `logger.exception` keeps it
except Exception:
    raise VosError(...)  # loses the cause; add `from e`
```

`raise X from e` always when translating. Without it the original traceback is gone and you debug the wrapper instead of the failure.

A broad catch is legitimate in exactly one place: the top of a worker loop, so one bad item does not kill the process — and there it logs with `logger.exception` and continues.

```python
for job in queue:
    try:
        handle(job)
    except Exception:
        logger.exception("job failed", extra={"job_id": job.id})
        continue
```

## Fail loudly at the boundary, degrade quietly inside

A validation error on input is a 400, immediately, with the field named. A missing optional thumbnail is a log line and a placeholder. The distinction is whether the caller can act on it.

## Logging

```python
logger = logging.getLogger(__name__)
logger.info("transcode complete", extra={"job_id": job.id, "duration_s": dt})
```

`__name__` so the logger name is the module path and filtering works. Structured fields in `extra`, not interpolated — `logger.info(f"job {id} done")` cannot be grouped or queried. `logger.exception` inside an `except` block; it attaches the traceback. Never `print` outside a CLI entry point: in a worker, stdout is either discarded or unstructured noise in the middle of JSON logs.

## Tests: behavior, not implementation

```python
def test_rejects_zero_bitrate() -> None:
    with pytest.raises(ValidationError) as ei:
        TranscodeJob(job_id=uuid4(), input_uri="https://x/y", target="h264", bitrate_kbps=0)
    assert ei.value.error_count() == 1
    assert ei.value.errors()[0]["loc"] == ("bitrate_kbps",)
```

Assert on the error's *shape* — which field, which code — not its message string. Messages are cosmetic and change with library versions; `loc` is the contract.

```python
@pytest.mark.parametrize(
    ("raw", "expected"),
    [("1:30", 90), ("0:05", 5), ("2:00:00", 7200)],
    ids=["mm:ss", "leading zero", "hh:mm:ss"],
)
def test_parse_duration(raw: str, expected: int) -> None:
    assert parse_duration(raw) == expected
```

`ids` so a failure names the case instead of printing `test_parse_duration[1:30-90]`.

## Fixtures

```python
@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(root=tmp_path)          # function scope: fresh per test
```

Default to function scope. A `scope="session"` fixture holding mutable state makes tests order-dependent, and the failure shows up as "passes alone, fails in CI". `tmp_path` over `/tmp` hardcoding — pytest cleans it and parallel runs do not collide.

Fake at your own seam, with a real object rather than `MagicMock`:

```python
class FakeBucket:
    def __init__(self) -> None:
        self.puts: dict[str, bytes] = {}

    async def put(self, key: str, data: bytes) -> None:
        self.puts[key] = data
```

`MagicMock` accepts any call, including misspelled methods and wrong arity, so a test keeps passing after you rename the method it was checking. A hand-written fake fails to construct.

`monkeypatch` for environment and module attributes; it undoes itself. `unittest.mock.patch` as a bare decorator stack over four dependencies is a sign the function has four too many dependencies.

## What not to test

Generated code, third-party behavior, and private helpers reached only through the public path. A test per private method locks in the current structure and makes refactoring expensive — which is the opposite of what the suite is for. Coverage of the public surface with real inputs beats line coverage of internals.
