# C-Laude

**Category:** Forensics · **Points:** 1000 · **Author:** adithG17

> Something doesn't quite add up. You have been given a collection of artifacts recovered from a small production environment — logs, network captures, service data, and filesystem remnants. Piece together the evidence, follow the traces, and answer the questions to uncover what happened.

**Flag:** `kBxAc{y35_f1n477y_y0u_f0und_17_r1g#+_175_r3l473d_70_t#3_4g3n71c_r4n50mw4r3_4tt4ck}`

> **Files:** `evidence.zip` — the recovered artifact bundle (binlogs, SQL snapshots, audit logs, two pcaps, and a filesystem collection). The live challenge served nine questions over `nc 35.232.188.8 31337`; each is worked through below.

---

## The short version

An attacker sent a malicious preview request to `edge-runner-02`. That request ran a shell command as the preview service account, planted an SSH key, and let the attacker log in a few seconds later. From the compromised worker, they downloaded a release profile containing several credentials, found the credential accepted by the Atlas configuration service, and used the database account exposed there to alter 37 production settings. They also installed a user-level systemd timer that called an outside telemetry host every 20 seconds.

The flag was:

```text
kBxAc{y35_f1n477y_y0u_f0und_17_r1g#+_175_r3l473d_70_t#3_4g3n71c_r4n50mw4r3_4tt4ck}
```

## Getting started

The attachment was a ZIP containing database binary logs, SQL snapshots, storage and authentication audit logs, two packet captures, and a small filesystem collection from the compromised preview worker.

```bash
unzip evidence.zip -d work
find work/evidence -type f -printf '%p\t%s bytes\n' | sort
```

The nine questions were served interactively:

```bash
nc 35.232.188.8 31337
```

Instead of treating every file separately, I first built a rough timeline. The important moment was **2026-10-03 12:08:27 UTC**. Around that second, the preview worker ran an unusual child process, accessed storage and Atlas, connected to MySQL, wrote persistence files, and then started making outbound connections.

> One small time-zone trap: `mariadb-binlog` displayed the database event as `08:08:27` in local Eastern time, while most JSON logs used `12:08:27+00:00`. The Unix timestamp in the binlog, `1791029307`, confirms that these are the same moment.

---

## Question 1: How many unique production configuration settings were modified?

**Answer:** `37`

The relevant files were:

```text
exports/ledger-01/binlog.000001
exports/ledger-01/binlog.000002
exports/ledger-01/binlog.000003
exports/ledger-01/pre-incident.sql
exports/ledger-01/post-incident.sql
exports/ledger-01/connection-audit.tsv
```

A MySQL binary log is basically a detailed transaction tape. It records database changes and, when decoded verbosely, shows the row values before and after each update. I decoded all three logs with:

```bash
mariadb-binlog --base64-output=DECODE-ROWS -vv \
  binlog.000001 binlog.000002 binlog.000003 > binlogs.txt
```

There were several small, ordinary-looking deployments elsewhere in the timeline. The suspicious transaction was the large one at `12:08:27 UTC` (`08:08:27` in the decoded local-time output). It updated configuration IDs `10` through `46`.

That range contains:

```text
46 - 10 + 1 = 37
```

IDs `10` through `15` appeared a second time in the same transaction, but the question asked for **unique** settings. Counting those repeated updates only once still gives **37**.

The SQL snapshots supported the result, but the binlog was more useful because it distinguished the one incident transaction from unrelated changes before and after it.

---

## Question 2: What user-level scheduled task was established?

**Answer:** `agent-cache.timer`

The worker collection included two sets of systemd units:

```text
checkpoint-sync.timer
checkpoint-sync.service
agent-cache.timer
agent-cache.service
```

`checkpoint-sync` was a normal root health check that had been running throughout the capture. `agent-cache.timer` suddenly appeared under the preview user's systemd directory at the incident time:

```text
2026-10-03T12:08:27.7938142900Z ... /home/svc_preview/.config/systemd/user/agent-cache.timer
```

Its contents were:

```ini
[Timer]
OnUnitActiveSec=20
```

Its matching service launched an unexpected script:

```ini
[Service]
ExecStart=/usr/local/bin/python /srv/callback_helper.py
```

The timer journal then showed `agent-cache.timer` running as `svc_preview` every 20 seconds. In ordinary terms, this was the attacker's recurring scheduled task.

---

## Question 3: Which release configuration object was retrieved?

**Answer:** `releases/2026.10/profile-r17.yaml`

The MinIO/S3-style audit log in `exports/vault-02/audit.jsonl` showed the worker listing the `release-assets` bucket at `12:08:27`, followed immediately by a successful download:

```json
{
  "api": {
    "name": "GetObject",
    "bucket": "release-assets",
    "object": "releases/2026.10/profile-r17.yaml",
    "status": "OK"
  },
  "remotehost": "10.60.20.42",
  "accessKey": "preview-reader"
}
```

The complete object path was therefore `releases/2026.10/profile-r17.yaml`.

The recovered copy of this object contained four tempting candidate secrets:

```yaml
poll_token: atlas-poll-6c2ad
rollout_token: atlas-rollout-b813f
storage_key_ref: preview-reader
runtime_token: atlas-runtime-91ef2
```

That led directly to the next question.

---

## Question 4: Which external IP initiated the malicious preview request?

**Answer:** `203.0.113.74`

The suspicious preview job was easy to spot in `preview-worker.jsonl` because every normal job used the `builtin` renderer, while one used `compat`:

```json
{
  "job_id": "preview-7f4a",
  "renderer_family": "compat",
  "event": "preview_completed",
  "time": "2026-10-03T12:08:07.165953+00:00"
}
```

`audit.log` tied that job to a shell child process:

```text
time=1791029287.166 ppid=29 uid=1000 comm=sh key=preview_child job=preview-7f4a
```

In `sensor/dmz.pcap`, the connection arriving at the worker's preview service (`203.0.113.42:8443`) at exactly that time came from `203.0.113.74`:

```bash
tshark -r dmz.pcap -q -z conv,tcp
```

The relevant conversation was:

```text
203.0.113.74:48544 <-> 203.0.113.42:8443
```

So `203.0.113.74` initiated the preview request associated with the shell execution.

---

## Question 5: Which credential did Atlas accept?

**Answer:** `runtime-r17`

After downloading the release profile, the compromised worker tried its candidate tokens against the production runtime endpoint. `exports/atlas-01/auth-audit.jsonl` recorded all three attempts:

```text
/v1/runtime/production  poll-r17     accepted=false
/v1/runtime/production  rollout-r17  accepted=false
/v1/runtime/production  runtime-r17  accepted=true
```

Only credential ID `runtime-r17` was accepted. Notice that the question requested the **credential ID**, not the token value `atlas-runtime-91ef2` from the YAML file.

---

## Question 6: Which created file was later used for SSH authentication?

**Answer:** `/home/svc_preview/.ssh/authorized_keys`

The filesystem timeline showed two SSH-related entries created when the anomalous preview ran:

```text
2026-10-03T12:08:07.1651575210Z ... /home/svc_preview/.ssh
2026-10-03T12:08:07.1651575210Z ... /home/svc_preview/.ssh/authorized_keys
```

Twenty seconds later, `auth.log` showed a successful public-key login to that same account:

```text
Accepted publickey for svc_preview from 203.0.113.74 port 42034 ssh2
```

The DMZ packet capture independently showed the SSH connection from `203.0.113.74` to port 22. The simplest explanation is that the malicious preview planted a public key in `authorized_keys`, after which the attacker used its matching private key to log in normally.

---

## Question 7: Which MySQL username modified the production data?

**Answer:** `svc_cfg_apply`

The database connection audit contained this connection at the exact incident time:

```text
2026-10-03 12:08:27.752844  [svc_cfg_apply] @ [10.60.20.42]  13  Connect
```

Here, `10.60.20.42` was the internal address of `edge-runner-02`, and `13` was the MySQL connection/thread ID. The suspicious transaction in the decoded binlog also had `thread_id=13`:

```text
#261003  8:08:27 ... Query thread_id=13
BEGIN
...
### UPDATE `claude_runtime`.`runtime_config`
```

Matching the thread ID and timestamp proves that the large configuration update came from the `svc_cfg_apply` account on the compromised worker.

Some updated JSON values contained `"updated_by": "deploy_agent"`, but that was just data stored inside the rows; it did not identify the authenticated database session. The connection/thread evidence is the reliable source here.

---

## Question 8: What error code came back from the file-write test?

**Answer:** `1290`

`session-errors.log` recorded the failed database operation immediately before the production changes:

```text
2026-10-03T12:08:27.755509+00:00 database client response:
(1290, 'The MySQL server is running with the --secure-file-priv option so it cannot execute this statement')
```

The attacker was checking whether MySQL could write a file on the server, a technique that can sometimes be abused to drop a payload or web shell. MySQL's `secure-file-priv` restriction blocked it and returned error **1290**. The failed check did not stop the attacker from continuing with ordinary database updates.

---

## Question 9: Which external host received the recurring connections?

**Answer:** `203.0.113.91`

The persistence timer began at `12:08:27` and repeated every 20 seconds:

```text
12:08:27  agent-cache.timer
12:08:47  agent-cache.timer
12:09:08  agent-cache.timer
```

The DMZ packet capture showed matching outbound TCP connections from the worker to `203.0.113.91:9443` at those same times:

```bash
tshark -r dmz.pcap \
  -Y 'ip.src==203.0.113.42 && tcp.flags.syn==1 && tcp.flags.ack==0' \
  -T fields -e frame.time -e ip.dst -e tcp.dstport
```

The results lined up almost perfectly:

```text
12:08:27  203.0.113.91  9443
12:08:47  203.0.113.91  9443
12:09:08  203.0.113.91  9443
```

DNS evidence in `sensor/queries.log` showed the worker resolving `telemetry-gateway.c-laude.test` at those times, and the TLS Client Hello in the packet capture used the same hostname as its SNI. The recurring external destination was therefore `203.0.113.91`.

---

## Reconstructed attack timeline

| Time (UTC) | What happened |
|---|---|
| 12:08:07 | `203.0.113.74` sent the anomalous `compat` preview request. A shell ran as `svc_preview` and created `~/.ssh/authorized_keys`. |
| 12:08:27 | The attacker logged in over SSH using the planted key. |
| 12:08:27 | The worker listed `release-assets` and downloaded `releases/2026.10/profile-r17.yaml`. |
| 12:08:27 | Candidate credentials were tried against `/v1/runtime/production`; `runtime-r17` succeeded. |
| 12:08:27 | `svc_cfg_apply` connected from the worker to MySQL. A database file-write attempt failed with error `1290`. |
| 12:08:27 | The same MySQL session modified 37 unique production configuration entries. |
| 12:08:27 | `agent-cache.timer` was installed for `svc_preview` and began running every 20 seconds. |
| 12:08:27 onward | The worker repeatedly connected to `203.0.113.91:9443`, using the hostname `telemetry-gateway.c-laude.test`. |

## Final answers

1. `37`
2. `agent-cache.timer`
3. `releases/2026.10/profile-r17.yaml`
4. `203.0.113.74`
5. `runtime-r17`
6. `/home/svc_preview/.ssh/authorized_keys`
7. `svc_cfg_apply`
8. `1290`
9. `203.0.113.91`

This challenge was mostly about correlation: no single artifact told the entire story. The useful part was noticing that the same host and second appeared across the preview log, filesystem timeline, storage audit, Atlas audit, MySQL logs, timer journal, and packet captures. Once those records were aligned, the intrusion chain became much clearer.
