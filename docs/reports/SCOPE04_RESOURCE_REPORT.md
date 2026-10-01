# SCOPE-04 Resource Report

Live Pi measurements below are short smoke samples, not capacity or endurance
claims. No unmeasured performance numbers are presented.

Repository-level resource safeguards implemented:

- camera queue uses a bounded `deque(maxlen=...)`;
- frames are read as transient bytes and are not written to disk;
- map cache is explicitly caller-supplied and offline-only;
- mock telemetry is one current sample, not an unbounded history;
- no listener, worker, subprocess, package installation, or systemd unit is
  started by import or test setup.

The live approval packet requires an operator to record actual Pi CPU, memory,
storage, service status, and listener observations during a separately
approved deployment. The repository-only fields above remain design claims;
the following are the measured Pi smoke values.

## Measured Pi smoke sample

| Metric | Idle | After one authenticated camera request |
|---|---:|---:|
| Process RSS | 48,240 KiB | 49,584 KiB |
| Process CPU sample | 24.5% | 25.9% |
| Threads | 1 | 1 |
| Open file descriptors | 7 | 7 |
| Load average (1/5/15) | 0.05 / 0.03 / 0.00 | 0.05 / 0.03 / 0.00 |

Host context at the same smoke: available memory `3,544 MiB`, `/home`
available storage `46 GiB`, listener `192.168.4.1:8443`. These are one short
sample, not capacity or endurance claims. The process was stopped after the
sample and no systemd unit was left running.
