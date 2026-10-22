# Baseline validation

Validation run: 22 October 2026, from main `76a455400b34b80a30ff2418a87ebb844fe8cab5` plus the baseline-readiness changes.

## Evidence

The local run used Docker Desktop 29.4.0, Python 3.12, and PostgreSQL 17. It started new containers and a new database volume from cached images. Isolation overrides removed host port publishing, the Docker socket mount, and PostgreSQL's restart policy. The workshop startup commands, migrations, seed script, and contract checks ran in those containers.

| Check | Result |
| --- | --- |
| Readiness regression | During dependency installation, the old `pgrep -f` check returned success while the startup shell was still running. |
| Startup wait | With the marker absent, the configured editor startup command waited 29.58 seconds, then succeeded; pandas, psycopg, and Alembic imports passed. The final Compose readiness wait and contract/count checks passed. |
| Restart | Restart cleared the readiness marker. The configured startup wait completed again and required imports passed. |
| Fresh database | All eight museum tables contained exactly the 3,025 IDs from the checked-in dataset. |
| Existing contracts | Both checks passed after startup. The separate test Compose run also exited 0 using `--exit-code-from devcontainer`. |
| Notebook kernel | The notebook's connection cell and count query ran through a Jupyter Python kernel; both counts were 3,025. |
| Breaking schema | The README's replacement `object_images` schema caused the contract test to fail on missing `primary_image` and `additional_images`. |
| Recovery | Restoring the original migration, upgrading, and seeding restored all IDs and passing contract checks. |
| Missing additive table | Adding the README's normalized contract before its table caused the expected coverage and constraint failures. |
| Additive repair | The README's normalized table and corrected contract passed both checks. Two different image URLs for one object were accepted; a duplicate object/URL pair was rejected. |
| Repeatable reset | Two resets restored all 3,025 IDs in every museum table and passing checks. The normalized exercise table was absent afterward. |

The rehearsal extracted migration and contract examples from the README into a temporary copy inside the test container. It changed only the isolated database and temporary exercise files. The repository's migration, seed script, dataset, original contract, and notebook remain at their starting versions.

Dataset SHA-256: `10eae3d1e7d8186e24dae68b4c783a7f5f841317f37ec9eb64ebf20527fd80cb`.

Local raw evidence is retained under the ignored `data/private/baseline/` directory: the rehearsal script, stage logs, JSON results, and executed notebook. These files are not part of the participant checkout.

## Startup behavior

Compose now clears `/tmp/workshop-ready` at startup and creates it only after dependency installation succeeds. Its health check reads that marker. The devcontainer configuration waits for the same marker, with a ten-minute timeout, before connecting the editor. This uses the standard [`postStartCommand` and `waitFor` lifecycle fields](https://github.com/devcontainers/spec/blob/main/docs/specs/devcontainerjson-reference.md).

CI waits for the development environment, runs the original contract checks, verifies the seeded count, and captures startup logs before stopping the containers.

## Review still required

The kernel check does not verify the Codespaces editor UI. Before closing the baseline task, Mark should open this branch in the intended Codespaces environment, select `/usr/local/bin/python`, run the README's count query, and confirm the failure → repair → reset teaching sequence. The original workshop starting schema must remain the starting point when the PR is merged.

The full AI workshop rehearsal, model benchmarks, question approval, and access/rights decisions remain separate tasks.
