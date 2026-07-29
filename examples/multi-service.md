# Follow a trace across two services

Instrument the second service the same way you instrumented the first, then
confirm that context propagates between them.

1. Add the client library to the downstream service and restart it.

2. Send one request through the upstream service.

3. Open the trace in the dashboard. A correlated trace shows both service
   names in the service column.

If the downstream spans appear as a separate trace, the `traceparent` header
is not surviving the hop. Check any proxy, load balancer, or API gateway
between the two services for a header allowlist.
