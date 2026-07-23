---
name: no-use-effect
description: |
  Prefer explicit React data flow and narrowly contain legitimate Effects.
  ACTIVATE when writing React components, refactoring existing useEffect calls,
  reviewing PRs with useEffect, or when an agent adds useEffect "just in case."
  Provides five replacement patterns plus reviewed external-system exceptions.
---

# No ad-hoc useEffect

Do not use `useEffect` for ordinary React data flow. Prefer derived state, event
handlers, reducers, data-fetching libraries, conditional rendering, or keyed
remounting. Keep Effects only when React must synchronize with an external
system, and contain those Effects in a narrowly named hook with complete cleanup.

## Quick Reference

- Lint rule: restrict direct `useEffect` in pages and components; allow reviewed synchronization hooks
- React docs: [You Might Not Need an Effect](https://react.dev/learn/you-might-not-need-an-effect)
- Origin: [https://x.com/alvinsng/status/2033969062834045089](https://x.com/alvinsng/status/2033969062834045089)

| Instead of useEffect for... | Use |
|----------------------------|-----|
| Deriving state from other state/props | Inline computation (Rule 1) |
| Fetching data | `useQuery` / data-fetching library (Rule 2) |
| Responding to user actions | Event handlers (Rule 3) |
| One-time external sync on mount | `useMountEffect` (Rule 4) |
| Reactive external sync | Named synchronization hook with exhaustive dependencies (Rule 4) |
| Resetting state when a prop changes | `key` prop on parent (Rule 5) |

## When to Use This Skill

- Writing new React components
- Refactoring existing `useEffect` calls
- Reviewing PRs that introduce `useEffect`
- An agent adds `useEffect` "just in case"

## Workflow

### 1. Identify the useEffect

Determine what the effect is doing -- deriving state, fetching data, responding
to an event, syncing with an external system, or resetting state. Do not remove
a valid external synchronization Effect merely to satisfy this skill.

### 2. Apply the Correct Pattern

Use the five rules below to pick the right replacement or containment boundary.

### 3. Verify

Use the repository's `AGENTS.md`, `CONTRIBUTING.md`, and package scripts to run
the relevant typecheck, focused tests, full test suite, and lint checks. Discover
the exact commands from the target repository instead of assuming a package
manager or project layout.

## The Escape Hatch: useMountEffect

For a true mount/unmount lifecycle with no reactive dependencies:

The implementation wraps `useEffect` with an empty dependency array to make intent explicit:

```typescript
export function useMountEffect(effect: () => void | (() => void)) {
  /* eslint-disable no-restricted-syntax */
  useEffect(effect, []);
}
```

Do not use `useMountEffect` to hide changing props, state, context, or callbacks.
That creates stale closures. If external synchronization must react to changing
values, keep an exhaustive dependency list inside a narrowly named custom hook.

## Replacement Patterns

### Rule 1: Derive state, do not sync it

Most effects that set state from other state are unnecessary and add extra renders.

```typescript
// BAD: Two render cycles - first stale, then filtered
function ProductList() {
  const [products, setProducts] = useState([]);
  const [filteredProducts, setFilteredProducts] = useState([]);

  useEffect(() => {
    setFilteredProducts(products.filter((p) => p.inStock));
  }, [products]);
}

// GOOD: Compute inline in one render
function ProductList() {
  const [products, setProducts] = useState([]);
  const filteredProducts = products.filter((p) => p.inStock);
}
```

**Smell test:** You are about to write `useEffect(() => setX(deriveFromY(y)), [y])`, or you have state that only mirrors other state or props.

### Rule 2: Use data-fetching libraries

Effect-based fetching creates race conditions and duplicated caching logic.

```typescript
// BAD: Race condition risk
function ProductPage({ productId }) {
  const [product, setProduct] = useState(null);

  useEffect(() => {
    fetchProduct(productId).then(setProduct);
  }, [productId]);
}

// GOOD: Query library handles cancellation/caching/staleness
function ProductPage({ productId }) {
  const { data: product } = useQuery({
    queryKey: ['product', productId],
    queryFn: () => fetchProduct(productId),
  });
}
```

**Smell test:** Your effect does `fetch(...)` and then `setState(...)`, or you are re-implementing caching, retries, cancellation, or stale handling.

### Rule 3: Event handlers, not effects

If a user clicks a button, do the work in the handler.

```typescript
// BAD: Effect as an action relay
function LikeButton() {
  const [liked, setLiked] = useState(false);

  useEffect(() => {
    if (liked) {
      postLike();
      setLiked(false);
    }
  }, [liked]);

  return <button onClick={() => setLiked(true)}>Like</button>;
}

// GOOD: Direct event-driven action
function LikeButton() {
  return <button onClick={() => postLike()}>Like</button>;
}
```

**Smell test:** State is used as a flag so an effect can do the real action, or you are building "set flag -> effect runs -> reset flag" mechanics.

### Rule 4: Contain external synchronization

Good uses: DOM integration, browser API subscriptions, sockets, timers,
third-party widget lifecycles, and analytics caused by a component becoming visible.

Use `useMountEffect` only for setup and cleanup that are truly tied to one mount.

```typescript
// BAD: Guard inside effect
function VideoPlayer({ isLoading }) {
  useEffect(() => {
    if (!isLoading) playVideo();
  }, [isLoading]);
}

// GOOD: Mount only when preconditions are met
function VideoPlayerWrapper({ isLoading }) {
  if (isLoading) return <LoadingScreen />;
  return <VideoPlayer />;
}

function VideoPlayer() {
  useMountEffect(() => playVideo());
}
```

Use `useMountEffect` for dependencies that are stable by contract (for example,
a module singleton or ref). Do not assume a context value is stable without
verifying its provider contract:

```typescript
// BAD: useEffect with dependency that never changes
useEffect(() => {
  connectionManager.on('connected', handleConnect);
  return () => connectionManager.off('connected', handleConnect);
}, [connectionManager]); // connectionManager is a singleton from context

// GOOD: useMountEffect for stable dependencies

useMountEffect(() => {
  connectionManager.on('connected', handleConnect);
  return () => connectionManager.off('connected', handleConnect);
});
```

**Smell test:** You are synchronizing with an external system, and the behavior is naturally "setup on mount, cleanup on unmount."

If the external system must resynchronize when a value changes, use a named hook
with a normal Effect and exhaustive dependencies:

```typescript
function useRoomConnection(roomId: string) {
  useEffect(() => {
    const connection = createConnection(roomId);
    connection.connect();
    return () => connection.disconnect();
  }, [roomId]);
}
```

The exception is the synchronization boundary itself, not permission to mix
derived state, event relays, or unrelated orchestration into that Effect.

### Rule 5: Reset with key, not dependency choreography

```typescript
// BAD: Effect attempts to emulate remount behavior
function VideoPlayer({ videoId }) {
  useEffect(() => {
    loadVideo(videoId);
  }, [videoId]);
}

// GOOD: key forces clean remount
function VideoPlayer({ videoId }) {
  useMountEffect(() => {
    loadVideo(videoId);
  });
}

function VideoPlayerWrapper({ videoId }) {
  return <VideoPlayer key={videoId} videoId={videoId} />;
}
```

**Smell test:** You are writing an effect whose only job is to reset local state when an ID/prop changes, or you want the component to behave like a brand-new instance for each entity.

## Component Structure Convention

Computed values come after hooks and local state, never via `useEffect`:

```typescript
export function FeatureComponent({ featureId }: ComponentProps) {
  // Hooks first
  const { data, isLoading } = useQueryFeature(featureId);

  // Local state
  const [isOpen, setIsOpen] = useState(false);

  // Computed values (NOT useEffect + setState)
  const displayName = user?.name ?? 'Unknown';

  // Event handlers
  const handleClick = () => { setIsOpen(true); };

  // Early returns
  if (isLoading) return <Loading />;

  // Render
  return <Flex direction="column" gap="lg">...</Flex>;
}
```
