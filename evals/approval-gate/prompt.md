I have a small Go CLI that reads a file from stdin and uploads it to an HTTP endpoint with one
PUT request. Add a `--retry` flag so failed uploads are retried three times with backoff.
