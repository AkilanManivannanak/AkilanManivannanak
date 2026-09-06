#!/usr/bin/env bash
# Set a description and topics on every repository, in one pass.
#
# The audit block on the profile flags repositories with no description, because
# GitHub search cannot find them and the repo grid reads as noise. This fixes all
# of them at once.
#
#   brew install gh          # if you don't have it
#   gh auth login            # HTTPS, browser flow
#   bash scripts/set_descriptions.sh
#
# Edit any line before running: the wording is a starting point, not gospel.
# Re-running is safe — it overwrites with the same values.

set -uo pipefail
U=AkilanManivannanak
ok=0; fail=0

set_repo () {
  local name="$1" desc="$2" topics="${3:-}"
  if gh repo edit "$U/$name" --description "$desc" ${topics:+--add-topic "$topics"} >/dev/null 2>&1; then
    printf '  ok    %s\n' "$name"; ok=$((ok+1))
  else
    printf '  FAIL  %s  (renamed, deleted, or no permission)\n' "$name"; fail=$((fail+1))
  fi
}

echo "Autonomous driving & BEV"
set_repo opendrivefm \
  "Camera-only BEV occupancy and trajectory prediction on nuScenes, with a camera-trust scorer and fault-injection harness. Fault AUROC 0.764, 71.2 FPS on 4 CPU threads." \
  "autonomous-driving,bev,perception,nuscenes,pytorch,computer-vision"
set_repo guardian-drive \
  "Multimodal driver-safety system: eight physiological and environmental hazard detectors fused with a BEV perception stack, arbitrated by a rule-based safety FSM." \
  "autonomous-driving,bev,sensor-fusion,tensorrt,cpp"
set_repo autonomy-vision \
  "SafeTruck-AV2: autonomous trucking stack with uncertainty-aware forecasting, deterministic guardrails and a Normal to Min-Risk fallback ladder." \
  "autonomous-driving,motion-forecasting,fastapi,safety"
set_repo Self-Driving-cars-Specialization \
  "CARLA motion planning: behavioural state machine, polynomial spiral path optimisation and collision checking. Zero collisions in evaluation." \
  "carla,motion-planning,self-driving"
set_repo Traffic-Sense-Ideathon \
  "Traffic-sensing concept submission for an ideathon." "ideathon,traffic"

echo "Agentic AI, LLM and RAG"
set_repo talentra_copilot \
  "Agentic hiring-intelligence platform: five LangGraph agents with PII redaction, bias auditing and a rule-based fallback at every layer. Eval p95 4.81 ms." \
  "langgraph,agents,llm,rag,fastapi"
set_repo neurapilot \
  "Agentic RAG tutoring engine on LangGraph with a semantic cache, quiz generation and RAGAS-style evaluation." \
  "rag,langgraph,chromadb,ollama"
set_repo phamilyops \
  "AI operations platform built as a pitch for a chronic-care company: 17 modules over FastAPI, Supabase pgvector and Claude, with EEOC-compliant bias auditing." \
  "fastapi,llm,healthcare,supabase"
set_repo attentive-flow \
  "Turns a marketing brief into a compliant multi-channel campaign, with a validate-and-auto-repair loop and a deterministic fallback when no LLM key is present." \
  "llm,fastapi,streamlit,automation"
set_repo stock-forecasting-aapl-LSTM-RAG \
  "Multi-horizon AAPL forecasting with LSTM and moving-average baselines, served behind FastAPI with a strictly grounded RAG copilot." \
  "lstm,forecasting,rag,fastapi,tensorflow"

echo "Retrieval and ranking"
set_repo two-stage-recommender-als-ranker-api \
  "CineWave: two-stage recommender with Spark ALS retrieval, a LightGBM ranker and bandit exploration. NDCG@10 0.1409, p95 under 50 ms." \
  "recommender-system,spark,lightgbm,bandits,fastapi"
set_repo FashionFinder \
  "Visual product search over 44,419 items comparing brute force, k-NN graph and FAISS IVF. 1.79 ms median, recall@10 0.90." \
  "faiss,visual-search,resnet,similarity-search"

echo "Healthcare and biomedical"
set_repo Esophageal-Cancer-Detection \
  "Endoscopic image screening with EfficientNet-B3 and channel attention on HyperKvasir: binary plus 8-class. 95.44% binary accuracy. Research only, not a medical device." \
  "medical-imaging,efficientnet,pytorch,classification"
set_repo AI-Powered-Multi-Disease-Health-Risk-Prediction \
  "Screening pipeline across 17 clinical conditions: Random Forest on tabular data, CNN on chest X-rays, SHAP explanations. Educational use only." \
  "healthcare,random-forest,cnn,shap"
set_repo Heart_disease_linear-regression "Coursework: regression on the heart-disease dataset." "coursework,regression"
set_repo Alcohol_prediction "Coursework: classification exercise on alcohol-consumption data." "coursework,classification"

echo "Speech, vision and signal"
set_repo noise-robust-kws-distress-detection \
  "Noise-robust keyword spotting for in-cabin distress phrases. 77.02% at 0 dB SNR, 0.43 MB model, p95 2.18 ms. Distress-class recall is 0.02 and being fixed." \
  "keyword-spotting,speech,edge-ai,cnn"
set_repo ASL-Alphabet-Recognition_A-Z_-Real-Time-Webcam-CNN \
  "Real-time webcam CNN classifying the ASL fingerspelling alphabet." "computer-vision,cnn,sign-language"
set_repo Image-Classification-using-CNN "Coursework: baseline CNN image classification." "coursework,cnn"

echo "Coursework and archive"
set_repo Bayesian-Network-Inference-Problem "Coursework: Bayesian network inference." "coursework"
set_repo Student-Performance-Using-Neural-Network "Coursework: neural network on student-performance data." "coursework"
set_repo Wine-Quality-using-Neural-Networks "Coursework: neural network on the wine-quality dataset." "coursework"
set_repo Forecasting-and-Predicting-of-stock-using-LSTM-algorithm-using-Machine-Learning- \
  "Undergraduate project: stock forecasting with LSTM." "coursework,lstm"
set_repo Pharmacy-management-system "Undergraduate project: pharmacy management system in Python." "coursework,python"
set_repo Library-Management-System-in-Python "Undergraduate project: library management system in Python." "coursework,python"
set_repo Android-App-for-Recycling-and-Donation-app "Undergraduate project: Android app for recycling and donation." "coursework,android,java"
set_repo AkilanPortfolio "Source for my portfolio site." "portfolio"
set_repo AkilanManivannanak "My GitHub profile: the perception deck, the animated hero, and the workflows that keep both current." "profile,readme,threejs"

echo
echo "done: $ok updated, $fail failed"
echo
echo "Two repositories are deliberately left out:"
echo "  costsim-ai       — empty. Delete it or put something in it."
echo "  Sign-Language-... — the name has two typos (Regonization, Meachine). Rename it first:"
echo "                      gh repo rename sign-language-recognition-cnn --repo $U/Sign-Language-Regonization-using-CNN-Algorithm-with-Meachine-Learning-Techniques-Paper"
