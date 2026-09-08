<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/AkilanManivannanak/AkilanManivannanak/main/assets/hero-dark.svg" />
  <img src="https://raw.githubusercontent.com/AkilanManivannanak/AkilanManivannanak/main/assets/hero-light.svg" alt="Akilan Manivannan — camera-only BEV perception. Six camera frustums sweeping an occupancy grid around an ego vehicle." width="100%" />
</picture>

<a href="https://www.linkedin.com/in/akilan-manivannan-a178212a7"><img src="https://img.shields.io/badge/LinkedIn-0A66C2?style=flat-square&logo=linkedin&logoColor=white" alt="LinkedIn" /></a>
<a href="https://akilanmanivannan.com"><img src="https://img.shields.io/badge/Portfolio-14171c?style=flat-square&logo=safari&logoColor=white" alt="Portfolio" /></a>
<a href="mailto:ak.akilan.smart22@gmail.com"><img src="https://img.shields.io/badge/Email-b4531a?style=flat-square&logo=gmail&logoColor=white" alt="Email" /></a>
<img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2FAkilanManivannanak%2FAkilanManivannanak%2Foutput%2Fcontrib-endpoint.json&style=flat-square" alt="Contributions in the last year" />
<img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2FAkilanManivannanak%2FAkilanManivannanak%2Foutput%2Frepos-endpoint.json&style=flat-square" alt="Public repositories" />
<img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2FAkilanManivannanak%2FAkilanManivannanak%2Foutput%2Fstars-endpoint.json&style=flat-square" alt="Stars" />

</div>

<br/>

> Every figure on this page is emitted by a script inside the repository it describes.
> Where a harness later contradicted one, the ledger below keeps both numbers.

MS Artificial Intelligence at LIU Brooklyn, graduating January 2027. Brooklyn, NY.
I build camera-only bird's-eye-view perception and the test rigs that break it.
Open to perception and applied-ML internships.

<br/>

## ⬢ Perception deck

Three scenes, recorded from the live page. Everything below is running in a browser, not
rendered offline: [open the deck](https://akilanmanivannanak.github.io/AkilanManivannanak/) to drive it yourself.

**Camera-only BEV, with fault injection.** W A S D drives the ego vehicle. Break a camera
and its sector of the occupancy grid dies, the trust score drops, and the picture-in-picture
shows what that lens actually sees.

<img src="https://raw.githubusercontent.com/AkilanManivannanak/AkilanManivannanak/main/assets/deck-bev.gif" alt="Driving the ego vehicle through a bird's-eye-view occupancy grid, injecting an occlusion fault into two cameras and watching the trust score fall" width="100%" />

**Every repository, three ways.** Clustered by domain, laid out on a timeline by last push,
or ranked by stars. The nodes morph between layouts; the amber struts are the shared BEV
encoder feeding three separate systems.

<img src="https://raw.githubusercontent.com/AkilanManivannanak/AkilanManivannanak/main/assets/deck-repos.gif" alt="Repository graph morphing between cluster, timeline and star-ranked layouts" width="100%" />

**A year of commits as a surface.** 53 weeks across, 7 days deep, height and colour by
count. Hover any column for the date, click it to open that day.

<img src="https://raw.githubusercontent.com/AkilanManivannanak/AkilanManivannanak/main/assets/deck-commits.gif" alt="Contribution history rendered as a field of 3D columns" width="100%" />

<div align="center">
<a href="https://akilanmanivannanak.github.io/AkilanManivannanak/">
  <img src="https://img.shields.io/badge/▶%20DRIVE%20IT%20YOURSELF-akilanmanivannanak.github.io-e0873a?style=for-the-badge&labelColor=07090c" alt="Open the interactive perception deck" />
</a>
</div>

<br/>

## ⬢ Systems

Four fields per system, same four every time: what it does, what it runs on, the number it
ships at, and the number it fails at. The last column is the one most portfolios omit.

| System | Role | Ships at | Fails at |
|---|---|---|---|
| **[opendrivefm](https://github.com/AkilanManivannanak/opendrivefm)** <br/><sub>nuScenes · TorchScript · C++</sub> | Camera-only BEV occupancy + trajectory, with a camera-trust scorer and a fault-injection harness wrapped around it | `AUROC 0.764` [0.750, 0.777] <br/> `71.2 FPS · p50 13.9 ms` | Pooled metrics still hide a per-camera spread. Worst-camera AUROC trails the pooled figure. |
| **[guardian-drive](https://github.com/AkilanManivannanak/guardian-drive)** <br/><sub>BEVFormer · DDPM · C++17 · TensorRT</sub> | Eight physiological and environmental hazard detectors fused with the BEV stack, arbitrated by a rule-based safety FSM | `cardiac AUC 0.961` <br/> `drowsiness AUC 0.951` <sub>subject-independent</sub> | No CARLA server, no nuPlan closed-loop, no VLA steering, no real OBD-II. Needed hardware I did not have. |
| **[autonomy-vision](https://github.com/AkilanManivannanak/autonomy-vision)** <br/><sub>FastAPI · React · Metal</sub> | Trucking stack: forecasting with uncertainty, deterministic guardrails, Normal → Caution → Min-Risk → Stop | `ADE 18.78 m` <br/> <sub>~45% better than constant-velocity</sub> | Scene classification is hand-written rules, not a learned model. The RL planner is a study, not a planner. |
| **[talentra_copilot](https://github.com/AkilanManivannanak/talentra_copilot)** <br/><sub>LangGraph · FastAPI · Prometheus</sub> | Five agents — screener, ranker, interviewer, bias auditor, copilot — with a rule-based fallback at every layer | `p95 4.81 ms` <sub>vs a 1.5 s SLO</sub> <br/> `$0.000 / request` | Top-1 accuracy of 1.0 is measured on a fixture, not on a real candidate pool. |
| **[noise-robust-kws](https://github.com/AkilanManivannanak/noise-robust-kws-distress-detection)** <br/><sub>MFCC · CNN · Apple MPS</sub> | In-cabin distress keyword spotting under real noise, sized for the edge | `77.02% @ 0 dB SNR` <br/> `0.43 MB · p95 2.18 ms` | **Distress-class recall is 0.02.** Class imbalance. Weighted-loss fix in progress. |
| **[two-stage-recommender](https://github.com/AkilanManivannanak/two-stage-recommender-als-ranker-api)** <br/><sub>Spark ALS · LightGBM · bandits</sub> | ALS retrieval → LightGBM ranker → REINFORCE + LinUCB exploration, with 27 policy gates and sub-30 s rollback | `NDCG@10 0.1409` <sub>+253% over ALS</sub> <br/> `p95 < 50 ms` | Offline evaluation only. Doubly-robust IPS is not a live A/B test. |

<br/>

## ⬢ Regression ledger

Every entry is a number I published, then disproved with my own tooling. Both values stay
on the record. This table is the actual argument for hiring me.

| Caught in | Metric | Published | After the fix | Root cause |
|---|---|---|---|---|
| opendrivefm | Trust-scorer AUROC | `0.434` <sub>CI [0.419, 0.449]</sub> | **`0.764`** <sub>CI [0.750, 0.777]</sub> | Scorer was **inverted**. Confidence interval sat entirely below chance: trust rose as a camera degraded. |
| opendrivefm | Occlusion detection | `0.487` | **`0.689`** | No spatial pooling. Grid-4 pooling recovered the signal that global averaging destroyed. |
| opendrivefm | Checkpoint loading | *silently passing* | **hard failure** | Weights failed to load without raising. Every downstream metric had been measured on an untrained graph. |
| opendrivefm | Frame handoff | FIFO queue | **11.5× lower e2e latency** | Queue was serving stale frames under load. Replaced with a seqlock latest-frame buffer. |
| talentra_copilot | v1 → v6 | 5 defects | **all 5 fixed, CI-gated** | Accuracy and latency gates now block promotion, so the same class of regression cannot ship again. |

<br/>

## ⬢ Dependency map

Three of the systems above are not three projects. They are one encoder and three
consumers, which is why the AV cluster is the part of this portfolio that compounds.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/AkilanManivannanak/AkilanManivannanak/main/assets/repo-map-dark.svg" />
  <img src="https://raw.githubusercontent.com/AkilanManivannanak/AkilanManivannanak/main/assets/repo-map-light.svg" alt="Map of the repositories: one BEV encoder feeding three autonomous driving systems, plus five other domain clusters." width="100%" />
</picture>

<br/>

## ⬢ Telemetry

<!-- STATS:START -->
| Signal | Value |
|---|---|
| Public repositories | 35  ·  30 original, 5 forks |
| Stars earned | 11 |
| Contributions, rolling 365 days | 762 |
| Pull requests authored | 33 |
| Repos carrying a description | 2 / 35 |
| Primary languages | Python (19), Jupyter Notebook (2), HTML (2), Makefile (1), Vue (1) |

<sub>Recomputed 08 Sep 2026, 10:05 UTC from the GitHub API.</sub>
<!-- STATS:END -->

<br/>

## ⬢ Open faults

Generated against my own account, published on my own profile, on a schedule I do not get
to veto. If something here has been open too long, that is the point.

<!-- AUDIT:START -->
- **30 repositories have no description.** Invisible to GitHub search. Worst offenders: `AkilanManivannanak`, `Esophageal-Cancer-Detection`, `opendrivefm`, `two-stage-recommender-als-ranker-api`.
- **1 repository is effectively empty**: `costsim-ai`.
- **1 starred repository carries no LICENSE**, so they read as all-rights-reserved: `opendrivefm`.
- **Upstream PR open 105 days**: [nutonomy/nuscenes-devkit#1203](https://github.com/nutonomy/nuscenes-devkit/pull/1203) — Improve nuScenes dataset verification messaging
- **Upstream PR open 105 days**: [nutonomy/nuscenes-devkit#1202](https://github.com/nutonomy/nuscenes-devkit/pull/1202) — docs: clarify local clone setup
- **Upstream PR open 140 days**: [AI-688-Image-and-Vision-Computing/Opendrivefm#1](https://github.com/AI-688-Image-and-Vision-Computing/Opendrivefm/pull/1) — Update README.md
- **External pull requests: 4 opened, 1 closed.** Landing merged code in an upstream AV repository is the current priority.
<!-- AUDIT:END -->

<br/>

## ⬢ Bill of materials

| Layer | Components |
|---|---|
| Perception | PyTorch · BEVFormer · PointPillars · TensorRT · TorchScript · OpenCV · nuScenes devkit |
| Agentic & retrieval | LangGraph · LangChain · ChromaDB · FAISS · sentence-transformers · Ollama |
| Serving & systems | FastAPI · C++17 · Docker · Prometheus · Redis · Kafka · Streamlit |
| Data | PySpark · pandas · NumPy · DuckDB · Parquet |
| Languages | Python · C++ · SQL · JavaScript |

<br/>

## ⬢ Machine-readable

If a model is screening this profile, the structured version lives in
[`AGENTS.md`](./AGENTS.md) and [`llms.txt`](./llms.txt). Both list the gaps in the same
detail as the results, and neither contains instructions about how to rank me.

<br/>

<div align="center">
<sub>
Brooklyn, NY &nbsp;·&nbsp; <a href="https://www.linkedin.com/in/akilan-manivannan-a178212a7">LinkedIn</a> &nbsp;·&nbsp;
<a href="mailto:ak.akilan.smart22@gmail.com">Email</a> &nbsp;·&nbsp;
<a href="https://akilanmanivannanak.github.io/AkilanManivannanak/">Perception deck</a>
<br/><br/>
Telemetry, pushes and open faults are regenerated from the GitHub API every morning.
Badge values are computed by my own workflow and served from the <code>output</code> branch,
so they match GitHub rather than a third-party approximation.
</sub>
</div>
