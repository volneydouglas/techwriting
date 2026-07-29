# Get started with Sentinel

Sentinel collects metrics, logs, and traces from your services and correlates
them by trace ID, so you can follow one request across every hop it made.

This guide takes about 20 minutes and gets you from nothing to a dashboard
showing live data from one service.

## Before you start

You need:

- A host with 4 GB of RAM and 20 GB of free disk. Below 4 GB the ingestion
  pipeline drops spans without logging an error — see
  [known memory limits](limits.md#ingestion-memory).
- Administrative access on that host. The installer writes to `/etc/sentinel`
  and registers a systemd unit.
- One service you can restart. Instrumentation takes effect on restart.

Sentinel runs on Linux and macOS. Windows is not supported.

## Install the agent

1. Download the package for your platform from the
   [supported platforms list](platforms.md).

2. Validate your configuration before you install:

   ```
   sentinel config validate ./sentinel.yaml
   ```

   The command exits non-zero and prints the failing key path if the file is
   malformed. It does not check whether the endpoints it names are reachable.

3. Run the installer:

   ```
   sudo ./sentinel-install --config ./sentinel.yaml
   ```

The installer starts the service and prints the dashboard URL. Open that URL
and confirm that the request-rate panel shows a non-zero value within about
60 seconds.

![Sentinel architecture: agents on each host forward to a collector, which
writes to storage and serves the dashboard](architecture.png)

## Instrument one service

Add the client library to your service and restart it:

```
pip install sentinel-client
```

```python
from sentinel import trace

@trace("checkout")
def handle_checkout(request):
    ...
```

The decorator emits one span per call. Nested calls to other instrumented
functions join the same trace.

## Troubleshoot

**No data in the dashboard after 5 minutes.** Check the agent log at
`/var/log/sentinel/agent.log`. Two causes account for most of these. Either a
firewall is blocking outbound port 4317, or the host clock differs from the
collector's by more than 30 seconds, which lands spans outside the retention
window.

**The service starts but reports `config: unknown key`.** Sentinel rejects
unknown configuration keys rather than ignoring them. Compare your file
against the [configuration reference](config.md).

**Spans appear but are not correlated.** The client propagates trace context
in the `traceparent` header. A proxy that strips unknown headers breaks
correlation; add `traceparent` to its allowlist.

## What Sentinel does not do

Sentinel samples at 100% by default and stores 7 days of traces. At sustained
rates above roughly 50,000 spans per second, storage becomes the bottleneck
before the collector does. Configure tail sampling before you reach that
point.

Sentinel does not alert. Route its metrics to your existing alerting system
through the [Prometheus remote-write endpoint](integrations.md#prometheus).

## Next

- [Configure tail sampling](sampling.md)
- [Add a second service and follow a trace across both](multi-service.md)
