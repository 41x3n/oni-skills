Find every place under the current working directory that constructs an HTTP client (for
example `http.Client{`, `requests.Session(`, `httpx.Client(`, `axios.create(`, or `new HttpClient(`),
and tell me which ones set a timeout. If there are none, say so.
