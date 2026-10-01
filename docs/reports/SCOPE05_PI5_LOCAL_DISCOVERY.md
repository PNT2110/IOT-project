# SCOPE-05 Autonomous Local Pi 5 Discovery

Assessment date: `2026-09-26` (Asia/Ho_Chi_Minh).

## Policy boundary

```text
OWNER_POLICY=AUTO_ONLY_NO_OWNER_INTERACTION
DISCOVERY_SCOPE=DIRECTLY_CONNECTED_PRIVATE_SUBNET_ONLY
PASSWORD_GUESSING=NOT_PERFORMED
PASSWORD_SCRAPING=NOT_PERFORMED
PUBLIC_SCAN=NOT_PERFORMED
```

Local context identified one directly connected private network:

```text
LOCAL_INTERFACE=enp3s0
LOCAL_ADDRESS=192.168.1.47/24
LOCAL_SUBNET=192.168.1.0/24
```

## Passive discovery

```text
PI5_DISCOVERY_METHOD=PASSIVE_MDNS_AND_NEIGHBOR
PI5_CANDIDATE_IPS=192.168.1.118
PI5_CANDIDATE_NAME=pitan.local
```

The candidate was present in the neighbor table and resolved through mDNS.
No public or whole-LAN scan was needed or performed.

## SSH-key attempt

```text
PI5_AUTH_METHOD=EXISTING_SSH_KEY_ONLY
PI5_SSH_TARGET=pitan@192.168.1.118
PI5_SSH_RESULT=PERMISSION_DENIED_PUBLICKEY
PI5_AUTH_STATE=NO_NONINTERACTIVE_AUTHORIZED_PATH
PI5_SHELL_UNAVAILABLE
```

The SSH attempt used `BatchMode`, disabled password and keyboard-interactive
authentication, and did not guess or submit credentials. The candidate's
server indicated password authentication as an alternative, which was not
used.

## USB consequence

```text
USB_DIAG_HOST=NOT_PI5
PI5_USB_EVIDENCE=NOT_COLLECTED
PI5_USB_DIAGNOSIS=BLOCKED_NO_EXISTING_AUTHORIZED_SHELL
NEXT_GATE=ONE_TIME_PI_ACCESS_BOOTSTRAP_REQUIRED
FLASH_GATE=BLOCKED
```

No `lsusb`, tty, sysfs or kernel USB command was run on the orchestration PC as
a substitute for Pi evidence.
