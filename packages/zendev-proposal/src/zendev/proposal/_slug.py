"""GitHub heading IDs using vendored github-slugger 0.0.3 character tables.

The source URL and ISC license are retained in github-slugger.json. Match its
UTF-16 character ranges without importing the Python-3.13-incompatible port.
"""

import json
import re
from importlib.resources import files

_data = json.loads(files("zendev.proposal").joinpath("github-slugger.json").read_text(encoding="utf-8"))
_pattern = re.compile(
    "|".join([f"[{_data['single_byte']}]", *(f"[{first}][{second}]" for first, second in _data["multi_byte"])])
)


class GithubSlugger:
    def __init__(self) -> None:
        self.used: set[str] = set()

    def slug(self, value: str) -> str:
        encoded = value.lower().encode("utf-16-le")
        units = "".join(
            chr(int.from_bytes(encoded[index : index + 2], "little")) for index in range(0, len(encoded), 2)
        )
        cleaned = _pattern.sub("", units).replace(" ", "-")
        original = cleaned.encode("utf-16-le", errors="surrogatepass").decode("utf-16-le")
        result = original
        count = 0
        while result in self.used:
            count += 1
            result = f"{original}-{count}"
        self.used.add(result)
        return result
