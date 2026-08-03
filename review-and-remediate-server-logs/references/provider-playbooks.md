# Provider Playbooks

Use only the section that matches the live environment. Replace placeholders with values discovered from configuration. Prefer structured output and bounded time windows.

## Google Cloud Run and Cloud Logging

Discover the project, region, services, and active revision:

```sh
gcloud config get-value project
gcloud run services list --platform managed --project PROJECT --region REGION
gcloud run services describe SERVICE --platform managed --project PROJECT --region REGION --format=json
```

Read a bounded service window:

```sh
gcloud logging read \
  'resource.type="cloud_run_revision" AND resource.labels.service_name="SERVICE" AND timestamp>="START_UTC" AND timestamp<="END_UTC"' \
  --project PROJECT --limit 500 --order desc --format=json
```

Useful filters:

```text
httpRequest.status>=500
severity>=ERROR
resource.labels.revision_name="REVISION"
jsonPayload.event="STRUCTURED_EVENT"
```

Query request logs separately from application logs when counts matter. Check `resource.labels.revision_name` before treating an event as current. Inspect Cloud Build or deployment history when artifact drift is plausible:

```sh
gcloud builds list --project PROJECT --region REGION --limit 20 --format=json
```

For secret mismatches, compare version metadata or SHA-256 digests without displaying the values. Accessing secret material and changing a secret are separate privileged actions; obtain authorization for each.

## AWS ECS and CloudWatch Logs

Discover the deployed service and task definition:

```sh
aws ecs describe-services --cluster CLUSTER --services SERVICE --output json
aws ecs describe-task-definition --task-definition TASK_DEFINITION --output json
```

Read a bounded log window. Convert timestamps to epoch milliseconds before invoking the command:

```sh
aws logs filter-log-events \
  --log-group-name LOG_GROUP \
  --start-time START_EPOCH_MS \
  --end-time END_EPOCH_MS \
  --limit 1000 \
  --output json
```

Use CloudWatch Logs Insights for grouping when available. Start with fields such as `@timestamp`, `@message`, `@logStream`, status, route, exception class, and structured event name. Confirm the ECS deployment or task-definition revision before mapping a failure to source.

## Kubernetes

Inventory workload and rollout state:

```sh
kubectl config current-context
kubectl -n NAMESPACE get deploy,pods -o wide
kubectl -n NAMESPACE rollout status deployment/DEPLOYMENT
kubectl -n NAMESPACE get deployment DEPLOYMENT -o json
```

Read bounded logs for every container selected by the workload:

```sh
kubectl -n NAMESPACE logs deployment/DEPLOYMENT --all-containers=true --since=1h --timestamps=true
kubectl -n NAMESPACE logs POD --container CONTAINER --previous --timestamps=true
kubectl -n NAMESPACE get events --sort-by=.lastTimestamp
```

Use `--previous` for crash-loop evidence, but verify whether the pod was replaced during a rollout. Do not infer application health from pod readiness alone.

## systemd and Host Services

Confirm unit state and read a bounded journal window:

```sh
systemctl status UNIT --no-pager
journalctl -u UNIT --since 'START' --until 'END' --output json
journalctl -u UNIT -p warning --since 'START' --no-pager
```

Confirm the running executable, environment source, and unit version before editing a checkout. Do not restart a unit unless explicitly authorized.

## Containers and Generic JSON Logs

Identify ownership before stopping or restarting anything:

```sh
docker ps --no-trunc
docker inspect CONTAINER
docker logs --since 1h --timestamps CONTAINER
```

For newline-delimited JSON, retain the original artifact and derive sanitized summaries:

```sh
jq -r '[.service, .revision, .httpRequest.status, .jsonPayload.event, .jsonPayload.error_class] | @tsv' logs.jsonl
```

Do not dump full records if they may contain request bodies, authorization headers, cookies, provider payloads, or user identifiers. Select an explicit safe field allowlist.

## Query Discipline

- Use absolute timestamps and record the timezone.
- Set a finite result limit, then widen deliberately if truncation is possible.
- Separate request/access logs from application logs before comparing counts.
- Group by stable fields rather than entire messages containing UUIDs or timestamps.
- Check active and retired revisions separately.
- Keep the original query alongside every count.
- Verify a success path as well as the failure path.
- Treat log exclusions, sampling, ingestion delay, and retention as evidence limitations.
