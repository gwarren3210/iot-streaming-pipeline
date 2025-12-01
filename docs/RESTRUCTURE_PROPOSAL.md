# Project Restructuring Proposal

## Current Problems

1. **Docker Compose deployment is fragmented**:
   - `/producers/` at root (Docker Compose only)
   - `/flink-job/` at root (Docker Compose only)
   - `/docker/` at root (infrastructure)
   - Should be self-contained like `/cloud/` and `/k8s/`

2. **Root directory clutter**:
   - Orphaned files like `flink_job_cloud.py`
   - Mixed concerns (components vs deployments)

3. **No clear separation**:
   - Hard to understand what belongs where
   - Duplicated code without clear shared location

4. **Inconsistent organization**:
   - `/cloud/` and `/k8s/` are self-contained
   - Docker Compose is spread across root

---

## Proposed Structure

```
iot-streaming-pipeline/
│
├── README.md                    # Main project overview, links to deployments
├── LICENSE
├── .gitignore
│
├── deployments/                 # All deployment methods
│   ├── docker-compose/
│   │   ├── README.md           # Docker Compose setup guide
│   │   ├── docker-compose.yml  # Infrastructure
│   │   ├── setup/
│   │   │   ├── setup_cassandra.cql
│   │   │   └── setup_cassandra.sh
│   │   ├── producer/
│   │   │   ├── Dockerfile
│   │   │   ├── iot_producer.py
│   │   │   └── requirements.txt
│   │   └── flink-job/
│   │       ├── Dockerfile
│   │       ├── flink_job.py
│   │       ├── download_kafka_jar.sh
│   │       ├── requirements.txt
│   │       └── flink-sql-connector-kafka.jar (gitignored)
│   │
│   ├── cloud/                  # Move existing /cloud/ here
│   │   └── [existing structure]
│   │
│   └── kubernetes/             # Rename from /k8s/
│       └── [existing structure]
│
├── components/                  # Shared/reusable components
│   ├── producers/
│   │   ├── base_producer.py    # Common producer logic
│   │   └── README.md
│   └── schemas/
│       ├── cassandra.cql       # Common schema definitions
│       └── avro/               # Avro schemas if shared
│
├── docs/                       # All documentation
│   ├── README.md               # Documentation index
│   ├── architecture.md         # Architecture diagrams
│   ├── deployment-comparison.md
│   ├── learnings/
│   │   ├── k8s_migration_walkthrough.md
│   │   └── configuration_learning.md
│   └── next-steps.md           # Move NEXT_STEPS.md here
│
└── scripts/                    # Shared utility scripts
    └── README.md
```

---

## Detailed Breakdown

### 1. `/deployments/` - All Deployment Methods

**Rationale**: Self-contained deployments make it clear what belongs to what. Each deployment has everything needed to run independently.

#### `/deployments/docker-compose/`
```
docker-compose/
├── README.md                   # Setup instructions
├── docker-compose.yml          # From /docker/docker-compose.yml
├── setup/                      # From /docker/setup_*.{cql,sh}
│   ├── setup_cassandra.cql
│   └── setup_cassandra.sh
├── producer/                   # From /producers/
│   ├── Dockerfile (new, for consistency)
│   ├── iot_producer.py
│   └── requirements.txt
└── flink-job/                  # From /flink-job/
    ├── Dockerfile (new, for consistency)
    ├── flink_job.py
    ├── download_kafka_jar.sh
    ├── requirements.txt
    └── flink-sql-connector-kafka.jar
```

**Benefits**:
- Everything for Docker Compose in one place
- Consistent with cloud/kubernetes structure
- Easy to find and understand

#### `/deployments/cloud/`
- Move existing `/cloud/` directory here
- Already well-organized, just relocate

#### `/deployments/kubernetes/`
- Rename `/k8s/` to `/kubernetes/` (full name, more professional)
- Structure already good, just rename

---

### 2. `/components/` - Shared Code

**Rationale**: If code is truly shared or provides base functionality, extract it here.

**Structure**:
```
components/
├── producers/
│   ├── base_producer.py        # Abstract base class
│   └── README.md
└── schemas/
    ├── cassandra.cql           # Common schema
    └── README.md
```

**When to use**:
- Common logic that's used by multiple deployments
- Base classes/utilities
- Shared schemas

**Note**: Only extract if truly shared. If deployments need different implementations, keep them separate.

---

### 3. `/docs/` - Centralized Documentation

**Rationale**: All documentation in one place, easier to find and maintain.

**Structure**:
```
docs/
├── README.md                   # Documentation index
├── architecture.md             # Architecture overview
├── deployment-comparison.md    # Comparison table
├── learnings/                  # From /learnings/
│   ├── k8s_migration_walkthrough.md
│   └── configuration_learning.md
└── next-steps.md               # From NEXT_STEPS.md
```

**Benefits**:
- Clear documentation location
- Can cross-reference easily
- Professional structure

---

### 4. `/scripts/` - Shared Utilities

**Rationale**: Utility scripts that might be used across deployments.

**Structure**:
```
scripts/
├── README.md
└── [utility scripts if any]
```

**Note**: Most scripts are deployment-specific and should stay in their deployment directories.

---

## Root Level Cleanup

### Keep at Root:
- `README.md` - Main project overview
- `LICENSE`
- `.gitignore`

### Remove from Root:
- `/producers/` → Move to `/deployments/docker-compose/producer/`
- `/flink-job/` → Move to `/deployments/docker-compose/flink-job/`
- `/docker/` → Move contents to `/deployments/docker-compose/`
- `/cloud/` → Move to `/deployments/cloud/`
- `/k8s/` → Move to `/deployments/kubernetes/`
- `/learnings/` → Move to `/docs/learnings/`
- `NEXT_STEPS.md` → Move to `/docs/next-steps.md`
- `flink_job_cloud.py` → Delete if unused, or move to appropriate location
- `PROJECT_ORGANIZATION.md` → Move to `/docs/`
- `RESTRUCTURE_PROPOSAL.md` → Move to `/docs/` or delete after migration

---

## Migration Steps

### Phase 1: Create New Structure (Non-Destructive)

1. Create new directories:
   ```bash
   mkdir -p deployments/{docker-compose,cloud,kubernetes}
   mkdir -p deployments/docker-compose/{setup,producer,flink-job}
   mkdir -p components/{producers,schemas}
   mkdir -p docs/learnings
   mkdir scripts
   ```

2. Move existing directories:
   ```bash
   git mv cloud deployments/cloud
   git mv k8s deployments/kubernetes
   git mv learnings docs/learnings
   ```

### Phase 2: Consolidate Docker Compose

3. Move Docker Compose components:
   ```bash
   git mv docker/* deployments/docker-compose/
   git mv docker/setup_cassandra.* deployments/docker-compose/setup/
   git mv producers deployments/docker-compose/producer
   git mv flink-job deployments/docker-compose/flink-job
   ```

4. Update references:
   - Update docker-compose.yml paths if needed
   - Update README.md paths
   - Update scripts

### Phase 3: Cleanup

5. Move/remove root files:
   ```bash
   git mv NEXT_STEPS.md docs/next-steps.md
   git mv PROJECT_ORGANIZATION.md docs/
   # Delete or move flink_job_cloud.py if unused
   ```

6. Remove empty directories:
   ```bash
   rmdir docker  # If empty
   ```

### Phase 4: Update Documentation

7. Update all README.md files with new paths
8. Update cross-references
9. Update .gitignore if needed

---

## Alternative: Simpler Restructure

If the full restructure is too much, here's a simpler approach:

```
iot-streaming-pipeline/
│
├── README.md
├── LICENSE
├── .gitignore
│
├── docker-compose/              # Consolidate here
│   ├── README.md
│   ├── docker-compose.yml       # From /docker/
│   ├── setup/                   # From /docker/
│   ├── producer/                # From /producers/
│   └── flink-job/               # From /flink-job/
│
├── cloud/                       # Keep as-is (already good)
├── kubernetes/                  # Rename from /k8s/
│
└── docs/                        # Documentation
    ├── learnings/               # From /learnings/
    └── next-steps.md            # From NEXT_STEPS.md
```

**Benefits of simpler approach**:
- Less disruptive
- Still fixes main issue (Docker Compose consolidation)
- Easier migration
- Can do full restructure later if needed

---

## Recommendation

**Start with the simpler restructure**, then evolve to the full structure if needed:

1. **Phase 1 (Immediate)**: Consolidate Docker Compose
   - Move `/producers/`, `/flink-job/`, `/docker/` → `/docker-compose/`

2. **Phase 2 (Quick)**: Clean up root
   - Move `/learnings/` → `/docs/learnings/`
   - Move `NEXT_STEPS.md` → `/docs/`
   - Rename `/k8s/` → `/kubernetes/`

3. **Phase 3 (Optional)**: Full restructure if needed
   - Move everything under `/deployments/`
   - Extract shared components

---

## Path Update Checklist

After migration, update paths in:

- [ ] `docker-compose.yml` (volume mounts, paths)
- [ ] All README.md files
- [ ] Scripts (setup_cassandra.sh, etc.)
- [ ] Documentation cross-references
- [ ] `.gitignore` patterns
- [ ] Dockerfiles (COPY paths)
- [ ] Kubernetes manifests (if they reference paths)

---

## Benefits of New Structure

1. **Clear separation**: Each deployment method is self-contained
2. **Consistency**: All deployments organized the same way
3. **Discoverability**: Easy to find what you need
4. **Maintainability**: Changes are isolated to deployment directories
5. **Professional**: Standard project structure
6. **Scalable**: Easy to add new deployment methods

---

## Questions to Consider

1. **Do we need `/components/` now?**
   - If code is deployment-specific, keep it separate
   - Only extract if truly shared

2. **Should we rename `/k8s/` to `/kubernetes/`?**
   - More professional, clearer
   - But requires updating all references

3. **Move to `/deployments/` subdirectory?**
   - Cleaner root, but adds nesting
   - Start simple, can nest later

---

## Decision Matrix

| Option | Complexity | Disruption | Benefits |
|--------|-----------|------------|----------|
| **Full Restructure** | High | High | Maximum organization |
| **Simple Restructure** | Medium | Low | Fixes main issues |
| **Minimal Change** | Low | Very Low | Just consolidate Docker Compose |

**Recommendation**: Start with **Simple Restructure** - fixes the main problems without excessive disruption.

