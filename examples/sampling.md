# Configure tail sampling

Head sampling decides before a trace completes, so it discards the slow traces
you most want. Tail sampling decides after, once latency and error status are
known.

Set the mode and the policy:

```yaml
sampling:
  mode: tail
  policies:
    - name: errors
      keep: all
      when: status == "error"
    - name: slow
      keep: all
      when: duration_ms > 500
    - name: baseline
      keep: 0.05
```

Policies are evaluated in order, and the first match wins. A trace matching no
policy is dropped.

Tail sampling holds each trace until it completes or times out at 30 seconds,
which raises collector memory in proportion to your open-trace count.
