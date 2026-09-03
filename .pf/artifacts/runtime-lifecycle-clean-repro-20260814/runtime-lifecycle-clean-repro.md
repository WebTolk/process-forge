# Clean isolated Runtime lifecycle reproduction

Result: PASS

## Trace-resolution limitation

The polling loop did not externally observe T3, T4, T5 before the child reached ready. T2 and T6 prove the surrounding durable states; service.py orders the missing transitions as starting-state write, HTTP bind/endpoint publication, then ready-state write. This is a measurement gap, not evidence of a failed transition.

## T0: runtime dir absent

```json
{
  "label": "T0: runtime dir absent",
  "lock": {},
  "process_exists": false,
  "readyz": {
    "status": "not_attempted"
  },
  "runtime_dir_exists": false,
  "service": {},
  "timestamp": "2026-08-14T09:25:04.898142Z"
}
```

## T1: runtime start called

```json
{
  "label": "T1: runtime start called",
  "lock": {},
  "process_exists": false,
  "readyz": {
    "status": "not_attempted"
  },
  "runtime_dir_exists": false,
  "service": {},
  "timestamp": "2026-08-14T09:25:07.260588Z"
}
```

## T2: lock written

```json
{
  "label": "T2: lock written",
  "lock": {
    "created_at": "2026-08-14T09:25:08Z",
    "instance_id": "c24e43ac53a54df980abf2268e69e04d",
    "pid": 4920
  },
  "process_exists": true,
  "readyz": {
    "status": "not_attempted"
  },
  "runtime_dir_exists": true,
  "service": {},
  "timestamp": "2026-08-14T09:25:08.293894Z"
}
```

## T6: CLI start returned

```json
{
  "cli": {
    "endpoint": "http://127.0.0.1:62604",
    "pid": 4920,
    "status": "started"
  },
  "label": "T6: CLI start returned",
  "lock": {
    "created_at": "2026-08-14T09:25:08Z",
    "instance_id": "c24e43ac53a54df980abf2268e69e04d",
    "pid": 4920
  },
  "process_exists": true,
  "readyz": {
    "body": {
      "ready": true,
      "status": "ready"
    },
    "http_status": 200
  },
  "runtime_dir_exists": true,
  "service": {
    "endpoint": "http://127.0.0.1:62604",
    "health": "ready",
    "instance_id": "c24e43ac53a54df980abf2268e69e04d",
    "pid": 4920,
    "processforge_core_version": "1.0.2",
    "protocol_version": "pf-runtime-poc-1",
    "runtime_version": "1.0.0-poc",
    "scheduler": {
      "jobs": {
        "director": {
          "last_result": "not_started",
          "period_seconds": 10
        },
        "inspector": {
          "last_result": "not_started",
          "period_seconds": 5
        },
        "ledger": {
          "last_result": "not_started",
          "period_seconds": 5
        },
        "projection": {
          "last_result": "not_started",
          "period_seconds": 30
        }
      }
    },
    "schema_version": 1,
    "started_at": "2026-08-14T09:25:08Z",
    "status": "ready",
    "token_hash": "sha256:3260c6e41c99363b7824aa11fc82d2a2c33c029b2c7833824653e92c677d82f8",
    "token_ref": "C:\\Users\\musst\\AppData\\Local\\Temp\\pf-runtime-clean-trace-n28fl3r1\\workplace\\runtime\\pf-runtime\\token.json",
    "updated_at": "2026-08-14T09:25:08Z",
    "workplace_id": "workplace",
    "workplace_root": "C:\\Users\\musst\\AppData\\Local\\Temp\\pf-runtime-clean-trace-n28fl3r1\\workplace"
  },
  "timestamp": "2026-08-14T09:25:08.458229Z"
}
```

## T7: session-register

```json
{
  "label": "T7: session-register",
  "lock": {
    "created_at": "2026-08-14T09:25:08Z",
    "instance_id": "c24e43ac53a54df980abf2268e69e04d",
    "pid": 4920
  },
  "process_exists": true,
  "readyz": {
    "body": {
      "ready": true,
      "status": "ready"
    },
    "http_status": 200
  },
  "runtime_dir_exists": true,
  "service": {
    "endpoint": "http://127.0.0.1:62604",
    "health": "ready",
    "instance_id": "c24e43ac53a54df980abf2268e69e04d",
    "pid": 4920,
    "processforge_core_version": "1.0.2",
    "protocol_version": "pf-runtime-poc-1",
    "runtime_version": "1.0.0-poc",
    "scheduler": {
      "jobs": {
        "director": {
          "last_result": "not_started",
          "period_seconds": 10
        },
        "inspector": {
          "last_result": "not_started",
          "period_seconds": 5
        },
        "ledger": {
          "last_result": "not_started",
          "period_seconds": 5
        },
        "projection": {
          "last_result": "not_started",
          "period_seconds": 30
        }
      }
    },
    "schema_version": 1,
    "started_at": "2026-08-14T09:25:08Z",
    "status": "ready",
    "token_hash": "sha256:3260c6e41c99363b7824aa11fc82d2a2c33c029b2c7833824653e92c677d82f8",
    "token_ref": "C:\\Users\\musst\\AppData\\Local\\Temp\\pf-runtime-clean-trace-n28fl3r1\\workplace\\runtime\\pf-runtime\\token.json",
    "updated_at": "2026-08-14T09:25:08Z",
    "workplace_id": "workplace",
    "workplace_root": "C:\\Users\\musst\\AppData\\Local\\Temp\\pf-runtime-clean-trace-n28fl3r1\\workplace"
  },
  "session_register": {
    "project": {
      "director_enabled": false,
      "effective_mode": "simple",
      "flow_root": ".pf",
      "project_id": "project",
      "project_root": "C:\\Users\\musst\\AppData\\Local\\Temp\\pf-runtime-clean-trace-n28fl3r1\\project"
    },
    "session_id": "clean-trace"
  },
  "timestamp": "2026-08-14T09:25:09.895420Z"
}
```

## T8: work-state

```json
{
  "label": "T8: work-state",
  "lock": {
    "created_at": "2026-08-14T09:25:08Z",
    "instance_id": "c24e43ac53a54df980abf2268e69e04d",
    "pid": 4920
  },
  "process_exists": true,
  "readyz": {
    "body": {
      "ready": true,
      "status": "ready"
    },
    "http_status": 200
  },
  "runtime_dir_exists": true,
  "service": {
    "endpoint": "http://127.0.0.1:62604",
    "health": "ready",
    "instance_id": "c24e43ac53a54df980abf2268e69e04d",
    "pid": 4920,
    "processforge_core_version": "1.0.2",
    "protocol_version": "pf-runtime-poc-1",
    "runtime_version": "1.0.0-poc",
    "scheduler": {
      "jobs": {
        "director": {
          "last_result": "not_started",
          "period_seconds": 10
        },
        "inspector": {
          "last_result": "not_started",
          "period_seconds": 5
        },
        "ledger": {
          "last_result": "not_started",
          "period_seconds": 5
        },
        "projection": {
          "last_result": "not_started",
          "period_seconds": 30
        }
      }
    },
    "schema_version": 1,
    "started_at": "2026-08-14T09:25:08Z",
    "status": "ready",
    "token_hash": "sha256:3260c6e41c99363b7824aa11fc82d2a2c33c029b2c7833824653e92c677d82f8",
    "token_ref": "C:\\Users\\musst\\AppData\\Local\\Temp\\pf-runtime-clean-trace-n28fl3r1\\workplace\\runtime\\pf-runtime\\token.json",
    "updated_at": "2026-08-14T09:25:08Z",
    "workplace_id": "workplace",
    "workplace_root": "C:\\Users\\musst\\AppData\\Local\\Temp\\pf-runtime-clean-trace-n28fl3r1\\workplace"
  },
  "timestamp": "2026-08-14T09:25:10.825909Z",
  "work_state_project": {
    "director_enabled": false,
    "effective_mode": "simple",
    "flow_root": ".pf",
    "project_id": "project",
    "project_root": "C:\\Users\\musst\\AppData\\Local\\Temp\\pf-runtime-clean-trace-n28fl3r1\\project"
  }
}
```

## T9: runtime stop called

```json
{
  "label": "T9: runtime stop called",
  "lock": {
    "created_at": "2026-08-14T09:25:08Z",
    "instance_id": "c24e43ac53a54df980abf2268e69e04d",
    "pid": 4920
  },
  "process_exists": true,
  "readyz": {
    "body": {
      "ready": true,
      "status": "ready"
    },
    "http_status": 200
  },
  "runtime_dir_exists": true,
  "service": {
    "endpoint": "http://127.0.0.1:62604",
    "health": "ready",
    "instance_id": "c24e43ac53a54df980abf2268e69e04d",
    "pid": 4920,
    "processforge_core_version": "1.0.2",
    "protocol_version": "pf-runtime-poc-1",
    "runtime_version": "1.0.0-poc",
    "scheduler": {
      "jobs": {
        "director": {
          "last_result": "not_started",
          "period_seconds": 10
        },
        "inspector": {
          "last_result": "not_started",
          "period_seconds": 5
        },
        "ledger": {
          "last_result": "not_started",
          "period_seconds": 5
        },
        "projection": {
          "last_result": "not_started",
          "period_seconds": 30
        }
      }
    },
    "schema_version": 1,
    "started_at": "2026-08-14T09:25:08Z",
    "status": "ready",
    "token_hash": "sha256:3260c6e41c99363b7824aa11fc82d2a2c33c029b2c7833824653e92c677d82f8",
    "token_ref": "C:\\Users\\musst\\AppData\\Local\\Temp\\pf-runtime-clean-trace-n28fl3r1\\workplace\\runtime\\pf-runtime\\token.json",
    "updated_at": "2026-08-14T09:25:08Z",
    "workplace_id": "workplace",
    "workplace_root": "C:\\Users\\musst\\AppData\\Local\\Temp\\pf-runtime-clean-trace-n28fl3r1\\workplace"
  },
  "timestamp": "2026-08-14T09:25:10.986606Z"
}
```

## T10: process exited

```json
{
  "label": "T10: process exited",
  "lock": {},
  "process_exists": false,
  "readyz": {
    "error": "<urlopen error timed out>",
    "status": "error"
  },
  "runtime_dir_exists": true,
  "service": {
    "endpoint": "http://127.0.0.1:62604",
    "health": "stopped",
    "instance_id": "c24e43ac53a54df980abf2268e69e04d",
    "pid": 4920,
    "processforge_core_version": "1.0.2",
    "protocol_version": "pf-runtime-poc-1",
    "runtime_version": "1.0.0-poc",
    "scheduler": {
      "jobs": {
        "director": {
          "last_result": "not_started",
          "period_seconds": 10
        },
        "inspector": {
          "last_result": "not_started",
          "period_seconds": 5
        },
        "ledger": {
          "last_result": "not_started",
          "period_seconds": 5
        },
        "projection": {
          "last_result": "not_started",
          "period_seconds": 30
        }
      }
    },
    "schema_version": 1,
    "started_at": "2026-08-14T09:25:08Z",
    "status": "stopped",
    "token_hash": "sha256:3260c6e41c99363b7824aa11fc82d2a2c33c029b2c7833824653e92c677d82f8",
    "token_ref": "C:\\Users\\musst\\AppData\\Local\\Temp\\pf-runtime-clean-trace-n28fl3r1\\workplace\\runtime\\pf-runtime\\token.json",
    "updated_at": "2026-08-14T09:25:12Z",
    "workplace_id": "workplace",
    "workplace_root": "C:\\Users\\musst\\AppData\\Local\\Temp\\pf-runtime-clean-trace-n28fl3r1\\workplace"
  },
  "stop_stdout": "RUNTIME: stopped",
  "timestamp": "2026-08-14T09:25:12.668178Z"
}
```

## T11: state cleanup

```json
{
  "label": "T11: state cleanup",
  "lock": {},
  "process_exists": false,
  "readyz": {
    "error": "<urlopen error timed out>",
    "status": "error"
  },
  "runtime_dir_exists": true,
  "service": {
    "endpoint": "http://127.0.0.1:62604",
    "health": "stopped",
    "instance_id": "c24e43ac53a54df980abf2268e69e04d",
    "pid": 4920,
    "processforge_core_version": "1.0.2",
    "protocol_version": "pf-runtime-poc-1",
    "runtime_version": "1.0.0-poc",
    "scheduler": {
      "jobs": {
        "director": {
          "last_result": "not_started",
          "period_seconds": 10
        },
        "inspector": {
          "last_result": "not_started",
          "period_seconds": 5
        },
        "ledger": {
          "last_result": "not_started",
          "period_seconds": 5
        },
        "projection": {
          "last_result": "not_started",
          "period_seconds": 30
        }
      }
    },
    "schema_version": 1,
    "started_at": "2026-08-14T09:25:08Z",
    "status": "stopped",
    "token_hash": "sha256:3260c6e41c99363b7824aa11fc82d2a2c33c029b2c7833824653e92c677d82f8",
    "token_ref": "C:\\Users\\musst\\AppData\\Local\\Temp\\pf-runtime-clean-trace-n28fl3r1\\workplace\\runtime\\pf-runtime\\token.json",
    "updated_at": "2026-08-14T09:25:12Z",
    "workplace_id": "workplace",
    "workplace_root": "C:\\Users\\musst\\AppData\\Local\\Temp\\pf-runtime-clean-trace-n28fl3r1\\workplace"
  },
  "timestamp": "2026-08-14T09:25:13.821857Z"
}
```
