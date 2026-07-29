# Supported platforms

| Platform | Architectures | Package |
|---|---|---|
| Linux (glibc 2.28+) | x86-64, arm64 | `.deb`, `.rpm`, `.tar.gz` |
| macOS 12+ | arm64 | `.pkg` |

Alpine and other musl-based distributions are not supported. The agent links
against glibc for its DNS resolver.

Windows support is not planned.
