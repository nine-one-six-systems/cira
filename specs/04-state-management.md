# State Management & Resume Specification

## Overview

The state management system enables pause/resume functionality for long-running analysis jobs. It persists checkpoints to allow recovery from interruptions without data loss or duplicate work.

## Functional Requirements

### Checkpointing (FR-STA-001 to FR-STA-004)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-STA-001 | Persist crawl state every 10 pages or 2 minutes | P0 |
| FR-STA-002 | Checkpoint stores: pages_visited, pages_queued, external_links_found, current_depth, timestamps, extraction counts, analysis progress | P0 |
| FR-STA-003 | Allow user to pause an in-progress analysis | P0 |
| FR-STA-004 | Allow user to resume a paused analysis | P0 |

### Recovery (FR-STA-005 to FR-STA-007)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-STA-005 | Automatically resume in_progress jobs on startup | P0 |
| FR-STA-006 | Handle timeout gracefully with checkpoint preservation | P0 |
| FR-STA-007 | Skip already-visited URLs on resume | P0 |

## Acceptance Criteria

### Checkpoint Persistence
- Checkpoint written every 10 pages OR every 2 minutes (whichever comes first)
- Checkpoint stored in CrawlSession.checkpointData (JSON column)
- Checkpoint includes all fields from CheckpointData interface
- Checkpoint survives server restart

### Pause Operation
- User can pause any in_progress job
- Immediate checkpoint save on pause
- Status changes to 'paused'
- Current activity completes gracefully (no mid-page interrupt)
- Workers release resources

### Resume Operation
- User can resume any paused job
- Checkpoint loaded and validated
- Status changes to 'in_progress'
- Crawling continues from queued pages
- Already-visited URLs skipped
- Analysis continues from last completed section

### Automatic Recovery
- On server startup, detect in_progress jobs
- Resume from last checkpoint
- Log recovery actions
- Handle stale jobs (no progress for 1 hour) - mark as failed

### Timeout Handling
- Time limit tracked from job start
- Remaining time calculated accounting for pauses
- Checkpoint saved before timeout
- Status set to 'timeout' (not 'failed')
- Partial results preserved

## Test Requirements

### Programmatic Tests

1. **Checkpoint Persistence Tests**
   - Checkpoint saved after 10 pages
   - Checkpoint saved after 2 minutes
   - Checkpoint contains all required fields
   - Checkpoint survives process restart

2. **Pause/Resume Tests**
   - Pause on in_progress job succeeds
   - Pause on completed/pending/paused returns error
   - Resume on paused job succeeds
   - Resume on non-paused job returns error
   - Resume skips visited URLs

3. **Recovery Tests**
   - Startup detects in_progress jobs
   - Jobs resume from checkpoint
   - Stale jobs marked as failed
   - Multiple jobs recovered correctly

4. **Timeout Tests**
   - Time limit triggers checkpoint
   - Status set to 'timeout'
   - Partial results accessible
   - Pause time not counted toward limit

### Edge Case Tests

1. **Checkpoint Corruption**
   - Invalid JSON handled gracefully
   - Missing fields use defaults
   - Fallback to fresh start if unrecoverable

2. **Concurrent Access**
   - Multiple resume attempts blocked
   - Only one worker processes job
   - Lock released on completion/pause

3. **Partial Progress**
   - Mid-page interrupt recoverable
   - Mid-extraction interrupt recoverable
   - Mid-analysis interrupt recoverable

## Data Models

### CheckpointData

```typescript
interface CheckpointData {
  pagesVisited: string[];
  pagesQueued: string[];
  externalLinksFound: string[];
  currentDepth: number;
  crawlStartTime: string;
  lastCheckpointTime: string;
  entitiesExtractedCount: number;
  analysisSectionsCompleted: string[];
}
```

### Job State

```typescript
interface JobState {
  companyId: string;
  status: CompanyStatus;
  phase: ProcessingPhase;
  startedAt: Date | null;
  pausedAt: Date | null;
  totalPausedDuration: number; // milliseconds
  checkpoint: CheckpointData;
}

enum CompanyStatus {
  PENDING = 'pending',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  FAILED = 'failed',
  PAUSED = 'paused'
}

enum ProcessingPhase {
  QUEUED = 'queued',
  CRAWLING = 'crawling',
  EXTRACTING = 'extracting',
  ANALYZING = 'analyzing',
  GENERATING = 'generating',
  COMPLETED = 'completed'
}
```

## State Transitions

```
PENDING -> IN_PROGRESS (job starts)
IN_PROGRESS -> PAUSED (user pauses)
IN_PROGRESS -> COMPLETED (job finishes)
IN_PROGRESS -> FAILED (unrecoverable error)
IN_PROGRESS -> TIMEOUT (time limit reached)
PAUSED -> IN_PROGRESS (user resumes)
PAUSED -> PENDING (user cancels and restarts)
COMPLETED -> IN_PROGRESS (rescan initiated)
TIMEOUT -> IN_PROGRESS (user resumes with extended time)
```

## Redis Keys

```
cira:job:{companyId}:status     - Current status
cira:job:{companyId}:progress   - Progress data for UI
cira:job:{companyId}:lock       - Distributed lock
cira:job:{companyId}:activity   - Current activity description
```

## Checkpoint Intervals

| Trigger | Condition |
|---------|-----------|
| Page count | Every 10 pages crawled |
| Time interval | Every 2 minutes |
| Phase transition | On entering new phase |
| User action | On pause request |
| Limit reached | Before timeout/page limit |

## Dependencies

- Redis for distributed locking and progress state
- SQLite for checkpoint persistence
- Celery for job orchestration
