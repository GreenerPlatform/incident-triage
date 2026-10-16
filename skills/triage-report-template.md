# Triage report template (reference)

Use with [SKILL.md](SKILL.md) Phase 2. This file is reference only, not a separate command.

## Report skeleton

```
══ INCIDENT TRIAGE ══
Alert   : <alert name>
Service : <service> (<namespace>)
Time    : <start_time>
Confidence: HIGH | MEDIUM | LOW — <one-sentence reason>

── SENTINEL STATE ──
[same table layout as /sentinel]

── CAUSATION CHAIN ──
  Candidate    → <description>  Evidence: <finding>
  Via          → <mechanism or INFERRED + verify command>
  Intermediate → <effect>
  Symptom      → <user-visible symptom>
  Alert        → <alert trigger>

── FIX PLAN ──
  P1: <action> + kubectl command + expected result
  P2: <confirm recovery>
  P3: <prevent recurrence or none>
```

## Candidate cause classification

Derive class from sentinel findings before you recommend a fix.

**OOMKill**

| Class | Signal | Action |
|-------|--------|--------|
| LIMIT TOO LOW | runtime under 5 min, memory climbing | Raise limit in config |
| POSSIBLE LEAK | long runtime, all replicas fail over time | Profile memory; do not raise limit blindly |
| INPUT TRIGGERED | kill on large requests | Fix input handling or cap size |

**CrashLoopBackOff** (use `Last State` exit code)

| Exit | Meaning | Action |
|------|---------|--------|
| 1 | App error | Escalate with logs |
| 137 | SIGKILL | Reclassify as OOMKill |
| 139 | SIGSEGV | Escalate to dev |
| 143 | SIGTERM | Check probe timing |

**ImagePullBackOff**: registry auth, missing tag, or network egress.

**Pending**: resource pressure, affinity, or unbound PVC.

**FailedMount**: missing Secret, ConfigMap, or PVC.

**HPA at max**: real load, `minReplicas == maxReplicas`, or metrics backend down.

**Probe failure**: slow startup, unhealthy app, or wrong port/path.

**Node NotReady**: network, kubelet, pressure, or node OOM cascade.

## Sanity checks for the reasoning layer

- A batch Job in the same namespace is not the root cause of a restart or latency alert unless evidence links them.
- Chronic hygiene (missing limits, node memory percent) is not an acute root cause.
- If the tool returns low confidence or exit code 3, lead with unclear root cause and list live checks (`kubectl describe pod`, restart counts).
