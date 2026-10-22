# Workshop model setup

The selected model is Gemma 4 E2B instruction-tuned, Q4_K_M, pulled from Docker Hub. Use a **4-core, 16 GB Codespace** for the workshop. Its roughly 4.09 GB download is not its RAM requirement: inference also needs working memory and a context cache, alongside PostgreSQL and the development environment. An 8 GB machine remains a test target, not a supported workshop configuration.

## Artifact and provenance

[`models/gemma.lock.json`](../models/gemma.lock.json) pins the model by SHA-256 manifest digest. [`compose.models.yaml`](../compose.models.yaml) pins the runner and Python client images by digest. Changing a tag on Docker Hub will not silently change these artifacts.

| Item | Selection |
| --- | --- |
| Hub model | `ai/gemma4:e2b-q4_K_M` |
| Model format | GGUF, Q4_K_M quantization |
| Model layers | 4,092,392,352 bytes, including the multimodal projector |
| Hub publisher | Docker, a verified publisher |
| Conversion source in registry metadata | `unsloth/gemma-4-E2B-it-GGUF` |
| Runtime | Docker Model Runner v1.2.9, llama.cpp CPU backend |
| Limits | 4 CPU cores, 6 GiB runner memory, no additional swap |
| Inference | 4,096-token context, one slot, four threads, 128 output tokens per check |

This is Docker's distribution of an Unsloth conversion of Google's model. It is **not a Google-published quantized artifact**. Digest pinning keeps the downloaded content fixed; publisher and conversion provenance are separate facts. The GGUF choice reflects the later decision to use the compact quantized Hub artifact.

Sources: [Docker Hub model](https://hub.docker.com/r/ai/gemma4), [Google's source model](https://huggingface.co/google/gemma-4-E2B-it), [conversion repository](https://huggingface.co/unsloth/gemma-4-E2B-it-GGUF), [runtime source at v1.2.9](https://github.com/docker/model-runner/tree/v1.2.9).

## Startup and dependencies

The devcontainer uses the original Compose file plus `docker-compose.workshop.yml`, which adds the model services and startup gate. The original `docker compose up` command still starts just the database exercise. Workshop startup follows this dependency chain:

1. `model-runner` starts and passes its backend health check.
2. `model-init` downloads the pinned artifact into the `model-cache` volume if it is absent, configures CPU inference, and requests a real text completion.
3. `devcontainer` starts only after model initialization succeeds and the existing PostgreSQL/ETL dependencies succeed.

Download progress alone does not pass the startup gate. Registry failures, incomplete pulls, inference errors and an incorrect startup answer fail initialization. The probe must return exactly `READY`. Warm startup reuses the model cache but repeats configuration and the inference check. Jinja template handling and `enable_thinking=false` are explicit so this text exercise receives answers within its output budget.

The runner exposes port 12434 only on the Compose network. The model services have no Docker socket or full repository mount. This is infrastructure for a future agent; it does not implement the agent, SQL tool, evaluator or gold-answer isolation.

This explicit runner service meets the requirement to run inside Compose without a host model installation. Docker's documented end-user path uses `docker model install-runner`; the Hub runtime image is described as an implementation component. Treat this Compose integration as pending Codespaces validation, not as a Docker-supported deployment recipe.

## Run the model independently

On native Linux with Docker Engine and Compose 2.20 or newer:

```sh
docker compose -f compose.models.yaml up -d model-init
docker compose -f compose.models.yaml logs -f model-init
docker compose -f compose.models.yaml run --rm model-check check
docker compose -f compose.models.yaml run --rm model-check benchmark --runs 3
```

The log must contain `"event": "model_ready"`, and `model-init` must exit with code 0. The check and benchmark print JSON containing the answer, elapsed time, finish reason and token usage. The first download needs network access to Docker Hub. Public pulls need no Hugging Face account or token; Docker Hub may impose rate limits.

For the full workshop, start/rebuild the devcontainer, or run `docker compose -f docker-compose.yml -f docker-compose.workshop.yml up -d`. `.devcontainer.json` requests four CPUs and 16 GB memory. Initial setup includes the 4.09 GB model download as well as container images and Python packages; the older README's 1–3 minute estimate does not apply to a cold model setup.

From inside the devcontainer:

```sh
python scripts/model_client.py check
python scripts/model_client.py benchmark --runs 3
```

The client reads `MODEL_RUNNER_URL=http://model-runner:12434` and the checked-in model lock. Its API endpoint is `/engines/llama.cpp/v1/chat/completions`. See the [Docker API reference](https://docs.docker.com/ai/model-runner/api-reference/).

## Validation and remaining gates

Local CPU validation passed on 22 October 2026. The test host was ARM64 Docker Desktop with 8,217,059,328 bytes (about 7.65 GiB) allocated to its Linux VM, a four-CPU runner quota, and the existing database and devcontainer running. It is not equivalent to a native AMD64 Codespace. No trace viewer or agent workload was running.

| Check | Observed result |
| --- | --- |
| Pinned Hub download | Completed and exact digest resolved |
| Cached startup after runner restart | 4.69 seconds for initializer to exit 0; exact `READY` answer |
| Reinitialize an already loaded model | Passed; probe took 0.913 seconds; no download |
| Three repeated short answers | 4.316 / 4.090 / 4.096 seconds; 26 output tokens each; all stopped normally |
| llama-server resident memory after final checks | 5,539,444 KiB, about **5.28 GiB**, including mapped model pages |
| Initial download/load cgroup peak | 6 GiB, reached the configured limit; zero OOM kills |
| Corrected-template run after restart | Zero OOM events/kills; cgroup peak about 3.12 GiB |
| Automated startup failure checks | Six passed |

The smaller post-restart cgroup value does **not** mean the model needs only 3.12 GiB: previously cached file pages can be charged outside the recreated cgroup. Use the process RSS and initial peak when planning headroom. The 6 GiB limit passed these short checks; full-context and agent workloads still need validation. The initial template configuration produced deliberation instead of a final answer; the final configuration explicitly enables Jinja and disables thinking, and passed the stricter probe.

Docker Desktop hides this runner from container listings; its inherited `com.docker.desktop.service` label appears to be responsible. On the tested installation (Compose 5.1.1) this causes Compose to report `model-init is missing dependency model-runner`. Local runtime testing therefore started the known test containers explicitly and used `run --no-deps` for checks. The native Linux Compose dependency path remains unverified; do not describe this setup as working on Codespaces until it passes there. The available GitHub CLI credentials lacked the `codespace` scope, so no Codespace was created or tested.

Before workshop acceptance, run a fresh 16 GB Codespace and record cold startup time, warm startup time, memory peak, and representative query latency with the database and selected viewer running. Then run the frozen evaluation and verify it fits the workshop time budget. Three short smoke prompts cannot establish that ten agent questions will finish on time. Only consider 8 GB after a full workload passes with memory headroom.

Useful memory diagnostics, run on the Docker host:

```sh
docker compose -f compose.models.yaml exec model-runner cat /sys/fs/cgroup/memory.peak
docker compose -f compose.models.yaml exec model-runner cat /sys/fs/cgroup/memory.events
docker stats --no-stream
```

`memory.peak` is in bytes and includes charged file cache; `docker stats` reports a different memory view. Check `oom` and `oom_kill`, not just whether a request returned. Preserve the named model volume when stopping the stack to avoid another download.

Run the startup failure tests without Docker:

```sh
python -m unittest discover -s tests -v
```
