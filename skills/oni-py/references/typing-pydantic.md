# Python typing and Pydantic v2

## Parse at the edge, pass models inward

Untrusted data becomes a model at the boundary — HTTP body, queue message, config file, LLM response — and stays a model everywhere below. A `dict[str, Any]` that flows three layers deep turns a schema mistake into a `KeyError` in an unrelated module at 3am.

```python
class TranscodeJob(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    job_id: UUID
    input_uri: AnyHttpUrl
    target: Literal["h264", "hevc", "av1"]
    bitrate_kbps: int = Field(gt=0, le=200_000)
```

`extra="forbid"` catches the renamed-field deploy where a producer sends `inputUri` and the consumer silently gets a default. `frozen=True` makes the model hashable and stops action-at-a-distance mutation. `Literal` over `str` turns an invalid enum into a validation error at the boundary instead of an `if/elif` that falls through to `else: pass`.

## Type the boundary tightly, the interior loosely

Annotate every parameter and return on anything crossing a module boundary. Inside a function, let inference work — annotating every local is noise.

```python
def select_rendition(
    job: TranscodeJob,
    available: Sequence[Rendition],
) -> Rendition | None:
```

- `Sequence` / `Mapping` / `Iterable` in parameters, concrete `list` / `dict` in returns. Accept broadly, return precisely.
- `X | None` over `Optional[X]`. Never a mutable default: `= None` then build inside.
- `Self` for fluent methods, `TypeVar` when input and output types are linked.
- `Final` for module constants.

`Any` is a declaration that checking stops here. Where the type genuinely isn't known, use `object` and narrow — the type checker then forces you to handle it.

## Validators for invariants the type cannot express

```python
class TimeRange(BaseModel):
    start: datetime
    end: datetime

    @model_validator(mode="after")
    def check_order(self) -> Self:
        if self.end <= self.start:
            raise ValueError("end must be after start")
        return self
```

`mode="after"` sees coerced fields and is the right place for cross-field rules. `mode="before"` is for reshaping raw input (accepting a legacy key name), not for validation. A `field_validator` that reaches for another field is a `model_validator` written in the wrong place.

## Discriminated unions instead of optional soup

```python
class ImageAsset(BaseModel):
    kind: Literal["image"] = "image"
    width: int
    height: int

class AudioAsset(BaseModel):
    kind: Literal["audio"] = "audio"
    duration_s: float

Asset = Annotated[ImageAsset | AudioAsset, Field(discriminator="kind")]
```

One model with every field optional forces every reader to re-derive which combination is legal. A discriminated union makes the illegal combinations unrepresentable, and `match asset:` becomes exhaustive.

```python
match asset:
    case ImageAsset(width=w, height=h): ...
    case AudioAsset(duration_s=d): ...
```

## Config is a model too

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VOS_", frozen=True)

    database_url: PostgresDsn
    bucket: str
    max_workers: int = 8

settings = Settings()  # fails at import if the environment is wrong
```

`os.environ["X"]` scattered through modules fails on the code path that first needs it — often minutes into a job. A settings model fails at startup, which is where you want it.

## Serialization

`model_dump(mode="json")` when the target is JSON — it converts `UUID`, `datetime`, and `Decimal`. Plain `model_dump()` leaves Python objects and the `json.dumps` two lines later raises. `model_dump(exclude_none=True)` for PATCH bodies where absent and null differ.

`TypeAdapter` for validating a bare collection without wrapping it in a model:

```python
adapter = TypeAdapter(list[TranscodeJob])   # build once, module level
jobs = adapter.validate_python(payload)
```

Building a `TypeAdapter` inside a hot function re-compiles the validator on every call.

## Make the checker mean something

```toml
[tool.mypy]
strict = true
warn_unreachable = true

[[tool.mypy.overrides]]
module = ["untyped_dep.*"]
ignore_missing_imports = true
```

`strict` or it will not catch the thing you added it for. Narrow the escape hatch to the specific untyped dependency rather than switching off a whole check globally. A `# type: ignore` carries a code and a reason: `# type: ignore[arg-type]  # upstream stub is wrong, see #412`.
