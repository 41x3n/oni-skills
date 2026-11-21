Update this TypeScript module for the approved task below. Return the complete revised
module, then briefly explain the change. This is a code-only fixture: you may read relevant
skill guidance, but do not execute the module, edit repository files, commit, or publish.

Fixture WORK.md setup: the human approved this single slice and its existing contracts.
The failing check is supplied by the fixture: a non-archived asset with
`publishAllowed: false` currently calls `prepare`, but the expected result is
`{ status: "skipped", assetId: asset.id }` with no dependency calls for that asset.
This setup is not evidence of a check run in the current session.

Task: add optional `publishAllowed?: boolean` to `Asset`. In `publishAssets`, skip
assets with explicit `false`, just like archived assets. Missing or `true` must retain
the current behavior. Apply the coding guidance to the changed module.

Preserve input order and sequential processing. Upload must finish before record runs.
Once preparation succeeds, always await discard after upload or record, including on
failure. Dependency rejections must still propagate; a failed preparation must not call
discard. Preserve all result shapes. Do not introduce libraries or unrelated behavior.

```typescript
type Asset = { id: string; sourceUrl: string; archived: boolean };
type PreparedAsset = { localPath: string };
type PublishResult =
  | { status: "published"; assetId: string; url: string }
  | { status: "skipped"; assetId: string };
type PublishDependencies = {
  prepare(asset: Asset): Promise<PreparedAsset>;
  upload(prepared: PreparedAsset): Promise<{ url: string }>;
  record(assetId: string, url: string): Promise<void>;
  discard(prepared: PreparedAsset): Promise<void>;
};
async function publishAsset(
  asset: Asset,
  dependencies: PublishDependencies,
): Promise<PublishResult> {
  const prepared = await dependencies.prepare(asset);
  try {
    const published = await dependencies.upload(prepared);
    await dependencies.record(asset.id, published.url);
    return { status: "published", assetId: asset.id, url: published.url };
  } finally {
    await dependencies.discard(prepared);
  }
}
export async function publishAssets(
  assets: Asset[],
  dependencies: PublishDependencies,
): Promise<PublishResult[]> {
  const results: PublishResult[] = [];
  for (const asset of assets) {
    if (asset.archived) {
      results.push({ status: "skipped", assetId: asset.id });
      continue;
    }
    results.push(await publishAsset(asset, dependencies));
  }
  return results;
}
```
