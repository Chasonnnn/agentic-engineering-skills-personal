# Provider evidence queries

Use only the relevant provider. Resolve placeholders from approved configuration and route cloud CLI leaf commands through authmux where required. Do not infer the target identity from ambient credentials. Commands are starting points for read-only evidence, not permission to deploy or restart.

## Cloud Run and Cloud Logging

List/describe the named service with explicit project and region. Select revision names, traffic allocations, and image identifiers; avoid dumping environment variables. Bound a service query by `resource.type="cloud_run_revision"`, service name, and absolute `timestamp` limits. Add the active revision filter when attributing current defects.

A safe request-log projection can select timestamp, revision, status, and severity:

```sh
gcloud logging read 'RESOURCE_AND_TIME_FILTER' --project PROJECT --limit 500 --order desc \
  --format='json(timestamp,resource.labels.revision_name,httpRequest.status,severity)'
```

Add application fields only after verifying their schema is safe. Do not select full URLs, textPayload, or arbitrary error messages by default. A 500-record sample is not a complete error count. Use complete bounded retrieval or an authorized aggregate query for counts; separate request and application streams.

Inspect deployment/build metadata if the local checkout does not explain the active revision. Secret version metadata can often establish drift without fetching secret values; actual secret access remains a separate authorized operation.

## ECS and CloudWatch

Query service deployments and task-definition identifiers with explicit cluster/account/region. Project only the needed fields; task definitions may contain environment values. `filter-log-events` can page through a bounded millisecond time window, but full messages may contain sensitive fields. Choose a known-safe structured projection or a Logs Insights query over vetted fields before emitting results.

If a local parser is necessary, keep unredacted data out of tool output and persisted scratch files. Preserve error and pagination status through the parser. Counts from limited events remain samples; verify completed Insights query status and its relevant limits before treating aggregates as complete.

## Kubernetes

Confirm context/namespace and selected workload. For deployment logs, explicitly include all selected pods as well as all containers when claiming workload-wide coverage. On versions supporting it:

```sh
kubectl -n NAMESPACE logs deployment/DEPLOYMENT --all-pods=true --all-containers=true \
  --since-time=START_UTC --timestamps=true --prefix=true
```

This command emits raw logs: use it only for a known-safe stream or route it through a vetted sanitizer before tool output. Check installed flag support. Otherwise enumerate matching pods and query each container; deployment shorthand alone may select one pod. Record upper query time and pod/revision coverage. Use per-pod `--previous` for previous-container crashes; replaced/deleted pods may require centralized retained logs. Readiness alone does not establish application health.

## systemd and containers

Use explicit unit/container identity and absolute journal/log bounds. Project only safe metadata from `systemctl`, deployment definitions, and `docker inspect`; full inspection can expose environment values. Sanitize selected log fields before emitting journal or container records. Confirm the running executable/image matches the source under investigation. Do not restart inherited services or store a raw log artifact merely for convenience.

## Coverage

Keep the exact query, identities, time bounds, selection/aggregation method, and completeness limits with each observation. Bound result size for exploration; make a separate completeness decision for counts. Sampling, exclusions, rotation, retention, replaced replicas, and ingestion delay can hide events. A successful query is not proof of a complete population.
