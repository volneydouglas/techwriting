# Integrations

## Prometheus

Sentinel exposes its metrics through a remote-write endpoint. Point your
Prometheus server at it:

```yaml
remote_write:
  - url: http://sentinel:9090/api/v1/write
```

Sentinel does not evaluate alert rules. Keep alerting in Prometheus or
Alertmanager, and use Sentinel for the trace context behind a firing alert.

## OpenTelemetry

The collector accepts OTLP over gRPC on port 4317 and OTLP over HTTP on port
4318. An existing OpenTelemetry SDK can point at Sentinel without changing
instrumentation.
