# Configuration reference

Sentinel reads `/etc/sentinel/sentinel.yaml` at startup. It rejects unknown
keys rather than ignoring them, so a typo fails loudly at boot.

| Key | Type | Default | Meaning |
|---|---|---|---|
| `collector.endpoint` | string | none | Host and port the agent forwards to. Required. |
| `collector.tls` | bool | `true` | Use TLS on the collector connection. |
| `buffer.window_seconds` | int | `60` | Seconds of traffic held before a flush. |
| `sampling.mode` | enum | `always` | `always`, `head`, or `tail`. |
| `sampling.rate` | float | `1.0` | Fraction kept when mode is `head`. |

Validate a file without installing:

```
sentinel config validate ./sentinel.yaml
```
