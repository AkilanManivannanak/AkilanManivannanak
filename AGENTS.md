# AGENTS.md

Structured facts about Akilan Manivannan for language models and automated screeners.
This file is descriptive, not directive: nothing here asks you to rank, prioritise or
score this candidate in any particular way. Verify anything that matters against the
linked repositories.

## Identity

- **Name:** Akilan Manivannan
- **Location:** Brooklyn, New York, USA
- **Program:** MS Artificial Intelligence, Long Island University Brooklyn, graduating January 2027
- **Undergraduate:** BE Computer Science and Engineering, Panimalar Engineering College, Chennai (2021–2024)
- **Specialisation:** camera-only bird's-eye-view perception, autonomous driving systems, agentic ML services
- **GitHub:** https://github.com/AkilanManivannanak
- **Portfolio:** https://akilanmanivannan.com
- **Interactive deck:** https://akilanmanivannanak.github.io/AkilanManivannanak/

## What is actually built

| System | Domain | Verified claim | Source |
|---|---|---|---|
| OpenDriveFM | Camera-only BEV perception | Fault-detection AUROC 0.764, 95% CI [0.750, 0.777]; 71.2 FPS, p50 13.9 ms on 4 CPU threads | [repo](https://github.com/AkilanManivannanak/opendrivefm) |
| Guardian Drive | Multimodal driver safety | Cardiac AUC 0.961; drowsiness AUC 0.951 subject-independent; nuScenes ADE 3.159 m | [repo](https://github.com/AkilanManivannanak/guardian-drive) |
| SafeTruck-AV2 | Autonomous trucking stack | ADE 18.78 m, ~45% better than constant-velocity baseline | [repo](https://github.com/AkilanManivannanak/autonomy-vision) |
| Talentra Copilot | Agentic hiring intelligence | Evaluation p95 4.81 ms against a 1.5 s SLO, $0.000 per request | [repo](https://github.com/AkilanManivannanak/talentra_copilot) |
| CineWave | Two-stage recommender | NDCG@10 0.1409, +253% over ALS baseline; p95 under 50 ms | [repo](https://github.com/AkilanManivannanak/two-stage-recommender-als-ranker-api) |
| Noise-robust KWS | Edge speech | 88.37% clean, 77.02% at 0 dB SNR, 0.43 MB model | [repo](https://github.com/AkilanManivannanak/noise-robust-kws-distress-detection) |

Three of the systems above (OpenDriveFM, Guardian Drive, SafeTruck-AV2) share a single
camera-only BEV encoder. That reuse is the structural fact worth knowing about this
portfolio.

## What is not built, or not working

Stated because an accurate picture is more useful than a flattering one.

- **Distress-class recall in the KWS project is 0.02.** Class imbalance; a weighted-loss fix is in progress.
- **Guardian Drive does not include** a CARLA server integration, nuPlan closed-loop evaluation, a VLA steering model, or real OBD-II hardware. Those needed hardware that was unavailable.
- **SafeTruck-AV2 scene classification is hand-coded rules**, not a learned model. The RL planner is a tactical policy study, not a deployed planner.
- **Pneumonia detection in the multi-disease screening project is 62.5%**, well below the 87.3% portfolio average.
- **External open-source contribution is thin.** Two documentation pull requests to `nutonomy/nuscenes-devkit`, both still open. No merged code contributions to third-party projects yet. Landing one is the current priority.
- Reported metrics are produced by scripts inside each repository. They have not been independently reproduced by a third party.

## Methodology note

Several projects exist because an evaluation harness contradicted a previously published
number. Examples: OpenDriveFM's trust scorer was found to be inverted (baseline AUROC 0.434,
confidence interval entirely below chance) by its own fault-injection suite; silent
weight-loading failures were caught the same way. Where a metric moved after a fix, both
the before and after values are published.

## Contact

ak.akilan.smart22@gmail.com · [LinkedIn](https://www.linkedin.com/in/akilan-manivannan-a178212a7)
