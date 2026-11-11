"""Read-only report of actual dimensions for published editorial covers.

This is an optional audit, not part of the importer or static-site build. Remote
image requests are bounded, concurrent, and non-fatal: a temporary CDN failure
is reported as unknown and never blocks publication.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import posts
from media_dimensions import image_dimensions, parse_image_dimensions

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 256 * 1024


def remote_dimensions(url):
    known = image_dimensions(url, root=ROOT)
    if known:
        return known, "known"
    try:
        request = Request(url, headers={
            "Range": "bytes=0-" + str(MAX_BYTES - 1),
            "User-Agent": "ZazoomTek-Media-Dimensions-Audit/1.0",
        })
        with urlopen(request, timeout=7) as response:
            data = response.read(MAX_BYTES)
        dimensions = parse_image_dimensions(data)
        return (dimensions, "fetched") if dimensions else (None, "unreadable")
    except (HTTPError, URLError, TimeoutError, OSError, ValueError):
        return None, "unavailable"


def main():
    rows = posts()
    sources = sorted({str(row.get("image") or "") for row in rows if row.get("image")})
    results = {}
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = {pool.submit(remote_dimensions, source): source
                   for source in sources if source.startswith(("http://", "https://"))}
        for source in sources:
            if source.startswith("/"):
                dimensions = image_dimensions(source, root=ROOT)
                results[source] = (dimensions, "local" if dimensions else "missing")
        for future in as_completed(futures):
            results[futures[future]] = future.result()

    measured = [(url, dims, method) for url, (dims, method) in results.items() if dims]
    unknown = [(url, method) for url, (dims, method) in results.items() if not dims]
    below = [(url, dims) for url, dims, _ in measured if dims[0] < 1200]
    non_wide = [(url, dims) for url, dims, _ in measured
                if not 1.70 <= dims[0] / dims[1] <= 1.85]

    print("COVER DIMENSIONS AUDIT")
    print("Unique covers:", len(sources))
    print("Measured:", len(measured), "| Unknown/unavailable:", len(unknown))
    print("Below 1200 px width:", len(below))
    print("Aspect ratio outside approximate 16:9 range:", len(non_wide))
    for url, dims in below[:30]:
        print("LOW WIDTH", str(dims[0]) + "x" + str(dims[1]), url)
    for url, dims in non_wide[:20]:
        print("NON 16:9", str(dims[0]) + "x" + str(dims[1]), url)
    for url, method in unknown[:20]:
        print("UNVERIFIED", method, url)


if __name__ == "__main__":
    main()
