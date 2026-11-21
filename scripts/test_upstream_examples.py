"""Execute the documented upstream error examples with Node's TypeScript support."""

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def node_supports_type_stripping() -> bool:
    """--experimental-transform-types needs Node 22.7 or newer."""
    node = shutil.which("node")
    if node is None:
        return False
    try:
        version = subprocess.run([node, "--version"], capture_output=True, text=True,
                                 timeout=5, check=True).stdout.strip().lstrip("v")
        major, minor = (int(part) for part in version.split(".")[:2])
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return (major, minor) >= (22, 7)


def example(path: str, heading: str) -> str:
    document = (ROOT / path).read_text()
    section = document.split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]
    match = re.search(r"```ts\n(.*?)\n```", section, re.DOTALL)
    if match is None:
        raise AssertionError(f"missing TypeScript example under {heading}")
    return match.group(1)


@unittest.skipUnless(node_supports_type_stripping(), "needs Node 22.7+ on PATH")
class UpstreamExamplesTest(unittest.TestCase):
    def test_upstream_errors_are_publicly_fixed_and_privately_minimal(self) -> None:
        timeout = example("skills/oni-ts/references/async.md", "Timeouts and cancellation")
        boundary = example("skills/oni-ts/references/boundaries.md", "One error shape, one mapping point")
        error_example = example("skills/oni-ts/references/async.md", "Errors keep their cause")
        error_class = re.search(r"class HttpError extends Error \{.*?\n\}", error_example, re.DOTALL)
        if error_class is None:
            self.fail("missing documented HttpError class")
        source = """
import assert from 'node:assert/strict'
__HTTP_ERROR__
class NotFoundError extends Error {}
class ZodError extends Error {}
const z = { ZodError }
const logs = []
const log = { error(...args) { logs.push(args) } }
let response
const fetch = async () => response
const Schema = { parse(value) { return value } }
const url = 'https://example.test/resource'
async function request() {
__TIMEOUT__
}
__BOUNDARY__
const secret = 'private-upstream-token-and-stack'
function checkResponse(error, upstreamStatus) {
  logs.length = 0
  assert.deepEqual(toResponse(error), {
    status: 502,
    body: { error: 'upstream', message: 'upstream request failed' },
  })
  assert.equal(logs.length, 1)
  assert.deepEqual(Object.values(logs[0][0]), [upstreamStatus])
  assert.equal(Object.keys(logs[0][0]).length, 1)
  assert.ok(!JSON.stringify(logs).includes(secret))
}
for (const status of [400, 401, 418, 429, 500, 503]) {
  logs.length = 0
  let textReads = 0
  response = {
    ok: false,
    status,
    async text() { textReads++; return secret },
    async json() { throw new Error('unexpected JSON read') },
  }
  let error
  try { await request() } catch (caught) { error = caught }
  assert.ok(error instanceof HttpError)
  assert.equal(error.status, status)
  assert.equal(error.message, 'upstream request failed')
  assert.equal(textReads, 0)
  assert.equal(logs.length, 0)
  checkResponse(error, status)
}
checkResponse(new HttpError(418, secret, { cause: new Error(secret) }), 418)
""".replace("__HTTP_ERROR__", error_class.group(0)).replace("__TIMEOUT__", timeout).replace("__BOUNDARY__", boundary)
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "examples.mts"
            script.write_text(source)
            result = subprocess.run(
                ["node", "--experimental-transform-types", str(script)],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
