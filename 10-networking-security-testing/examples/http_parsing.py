"""
10 — Networking Deep Dive: Parsing an HTTP/1.1 Request & Response by Hand
=======================================================================

Runnable companion to PDF Book VII, Chapter "HTTP & the Web".

HTTP is just text over TCP. Parsing a raw request/response demystifies what
frameworks do for you: a request line, headers (CRLF-separated), a blank line,
then an optional body. This is the wire format behind every REST call.

    request-line   ->  GET /path?q=1 HTTP/1.1
    headers        ->  Host: api.example.com\r\n ... (case-insensitive names)
    blank line     ->  \r\n   (separates headers from body)
    body           ->  bytes, length given by Content-Length

Run:  python http_parsing.py
"""

from __future__ import annotations

from dataclasses import dataclass, field

CRLF = "\r\n"


@dataclass
class HttpRequest:
    method: str
    target: str
    version: str
    headers: dict = field(default_factory=dict)
    body: str = ""

    def header(self, name: str) -> str | None:
        return self.headers.get(name.lower())          # header names are case-insensitive


def parse_request(raw: str) -> HttpRequest:
    head, _, body = raw.partition(CRLF + CRLF)         # blank line splits head/body
    lines = head.split(CRLF)
    method, target, version = lines[0].split(" ")
    headers: dict[str, str] = {}
    for line in lines[1:]:
        name, _, value = line.partition(":")
        headers[name.strip().lower()] = value.strip()  # normalize to lowercase keys
    return HttpRequest(method, target, version, headers, body)


def build_response(status: int, reason: str, body: str,
                   headers: dict | None = None) -> str:
    headers = dict(headers or {})
    headers.setdefault("Content-Type", "text/plain")
    headers["Content-Length"] = str(len(body.encode()))  # framing: how many body bytes
    lines = [f"HTTP/1.1 {status} {reason}"]
    lines += [f"{k}: {v}" for k, v in headers.items()]
    return CRLF.join(lines) + CRLF + CRLF + body


# A tiny status-class helper — the leading digit is the category.
def status_class(code: int) -> str:
    return {1: "informational", 2: "success", 3: "redirect",
            4: "client error", 5: "server error"}[code // 100]


def demo() -> None:
    raw = (
        "POST /orders?debug=1 HTTP/1.1" + CRLF +
        "Host: api.example.com" + CRLF +
        "Content-Type: application/json" + CRLF +
        "Content-Length: 13" + CRLF +
        CRLF +
        '{"total":42}'
    )
    req = parse_request(raw)
    assert req.method == "POST"
    assert req.target == "/orders?debug=1"
    assert req.version == "HTTP/1.1"
    # Header lookup is case-insensitive.
    assert req.header("HOST") == "api.example.com"
    assert req.header("content-type") == "application/json"
    assert req.body == '{"total":42}'
    print(f"parsed: {req.method} {req.target}  host={req.header('host')}  body={req.body}")

    # Build a response and prove the framing (Content-Length matches the body).
    resp = build_response(201, "Created", '{"id":"o1"}', {"Content-Type": "application/json"})
    head, _, body = resp.partition(CRLF + CRLF)
    assert head.splitlines()[0] == "HTTP/1.1 201 Created"
    assert f"Content-Length: {len(body.encode())}" in head
    print("built response:", head.splitlines()[0])

    # Status classes by leading digit.
    assert status_class(200) == "success"
    assert status_class(301) == "redirect"
    assert status_class(404) == "client error"
    assert status_class(503) == "server error"
    print("status classes: 200=success 301=redirect 404=client error 503=server error")


def main() -> None:
    print("=" * 68)
    print("HTTP/1.1 request & response parsing by hand")
    print("=" * 68)
    demo()
    print("\nAll HTTP-parsing demos passed ✔")


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
