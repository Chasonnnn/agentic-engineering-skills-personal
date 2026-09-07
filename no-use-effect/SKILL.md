---
name: no-use-effect
description: Review or replace unnecessary React Effects while preserving dependency-correct external synchronization.
---

# No ad-hoc useEffect

Prefer explicit React data flow. Do not remove a valid external synchronization Effect merely to satisfy this skill. Use the project's existing architecture and libraries; an Effect alone is not a reason to install a query library or add lint policy.

| Purpose | Preferred approach |
|---|---|
| Derive values from props/state | Compute during render; memoize only when useful |
| Respond to a user action | Perform the action in its event handler |
| Fetch application data | Existing framework loader, server data path, or query library |
| Reset all local state for a new entity | Key the owning component when a full remount is intended |
| Synchronize an external system | Named hook with a normal Effect, exhaustive dependencies, and cleanup |

## External synchronization

Keep each Effect focused on one external resource. Declare every reactive value it reads, including callbacks. A stable connection object does not make a captured callback stable. Avoid generic `useMountEffect(callback)` wrappers that hide dependency analysis; prefer hooks named for the synchronization they perform.

```typescript
function useRoomConnection(roomId: string) {
  useEffect(() => {
    const connection = createConnection(roomId);
    connection.connect();
    return () => connection.disconnect();
  }, [roomId]);
}
```

Empty dependencies are appropriate only when setup reads no reactive values. They do not promise execution exactly once: cleanup and setup must tolerate development Strict Mode and remounts. Keep subscriptions, timers, and widgets reversible where their APIs support it. Do not treat a conditional Effect as inherently wrong; condition changes may be the intended synchronization.

For example, synchronizing video playback with a reactive playing state is legitimate external synchronization. Moving it behind conditional mounting can change state preservation and lifecycle behavior, so it is not an equivalent default rewrite.

## Data and reset boundaries

A query library can coordinate caching and stale results. Request cancellation requires using its supplied AbortSignal in the transport; a query function that ignores it does not cancel the underlying request automatically. Retain relevant loading/error behavior when replacing an Effect. If the project uses direct Effect fetching, preserve dependency correctness and stale-response protection.

Use `key` when changing entity identity should reset the entire component subtree, including local state and focus. It is too broad when only one field should change or an external resource should resynchronize. For a new document editor, `<Editor key={documentId} documentId={documentId} />` may express an intentional fresh editor; inspect the intended state lifetime first.

Validate changed observable behavior and relevant cleanup or race paths with the project's focused checks. Run broader suites when required by project rules or affected scope, not for every Effect edit.

[React: unnecessary Effects](https://react.dev/learn/you-might-not-need-an-effect) · [React: Effect lifecycle](https://react.dev/reference/react/useEffect) · [TanStack Query cancellation](https://tanstack.com/query/latest/docs/framework/react/guides/query-cancellation)
