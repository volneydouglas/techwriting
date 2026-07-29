# Limits

## Ingestion memory

The collector buffers spans in memory before writing them to storage. The
buffer holds 60 seconds of traffic.

Below 4 GB of RAM the buffer is sized too small for its own flush interval.
Spans are then dropped at the buffer boundary, and because the drop happens
before the metrics pipeline, nothing records it. The dashboard shows a lower
span count with no error.

Give the collector 4 GB, or lower `buffer.window_seconds` to 20.

## Retention

Traces are kept for 7 days. Metrics are kept for 400 days at 1-minute
resolution.
