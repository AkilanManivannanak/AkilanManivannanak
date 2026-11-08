#!/usr/bin/env python3
"""What every repository is, which category it belongs to, and what it is built with.

Three layers, checked in order, so the profile stays accurate for old and new repos alike:

1. CURATED: hand-checked entries for every existing repo, written from each repo's own
   README and code. These always win.
2. The repo itself: its GitHub description, topics and README. A new repo is categorised
   from these and its one-line description is lifted from the first real sentence of its
   README, so a new repo never shows up as "description pending".
3. A clean fallback built from the repo name and language, used only when a repo has no
   description and no README at all.
"""

import re

# Category order on the profile. Keys are stable ids used in file names and the deck.
DOMAINS = [
    ("av",      "Autonomous driving & BEV",   "🚗"),
    ("agentic", "Agentic AI · LLM · RAG",     "🤖"),
    ("rank",    "Search, retrieval & ranking", "🔎"),
    ("health",  "Healthcare & biomedical AI", "🩺"),
    ("signal",  "Speech & computer vision",   "🎙️"),
    ("finance", "Finance & forecasting",      "📈"),
    ("ml",      "Classical machine learning", "🧮"),
    ("apps",    "Software & web apps",        "🧩"),
    ("forks",   "Open-source forks",          "🍴"),
]
DOMAIN_ORDER = [d for d, _, _ in DOMAINS]
LABELS = {d: l for d, l, _ in DOMAINS}
ICONS = {d: i for d, _, i in DOMAINS}

# Never shown in the catalog. Empty repos are hidden automatically as well (see hidden()).
HIDE = {"Initialize-this-repository"}

# name: (domain, one-line description, stack)
CURATED = {
    # Autonomous driving & BEV
    "opendrivefm": ("av",
        "Camera-only BEV occupancy and 6 s trajectory prediction on nuScenes with per-camera trust scoring. Fault AUROC 0.764 at 71.2 FPS.",
        "PyTorch · nuScenes · C++"),
    "guardian-drive": ("av",
        "Driver-safety stack: eight hazard detectors fused with BEV perception under a safety state machine. Cardiac AUC 0.961.",
        "BEVFormer · TensorRT · C++17"),
    "autonomy-vision": ("av",
        "SafeTruck-AV2: autonomous trucking prototype with BEV perception, uncertainty-aware forecasting and safety guardrails. ADE 18.78 m.",
        "FastAPI · React · nuScenes"),
    "Self-Driving-cars-Specialization": ("av",
        "Full CARLA motion-planning stack: behavioural planner, polynomial spiral paths, collision checking and velocity profiles.",
        "Python · CARLA"),
    "Traffic-Sense-Ideathon": ("av",
        "TrafficSense: forecasts congestion 5 to 15 minutes ahead and turns it into constraint-aware adaptive signal timing.",
        "ML · smart-city pitch"),
    # Agentic AI
    "talentra_copilot": ("agentic",
        "Compound AI hiring platform: five LangGraph agents with semantic retrieval, PII redaction and fallbacks. p95 4.81 ms.",
        "LangGraph · FastAPI · Prometheus"),
    "phamilyops": ("agentic",
        "AI-native care operations platform: HR workflow automation plus a RAG copilot over Supabase and pgvector.",
        "Claude API · FastAPI · pgvector"),
    "attentive-flow": ("agentic",
        "AttentiveFlow: agentic lifecycle marketing, from brief to audience, messages, compliance checks, scoring and auto-repair.",
        "LLM agents · Streamlit"),
    # Search, retrieval & ranking
    "two-stage-recommender-als-ranker-api": ("rank",
        "CineWave: ALS retrieval plus a LightGBM LambdaRank ranker with bandit exploration. NDCG@10 0.1409, +253% over ALS.",
        "Spark ALS · LightGBM · GraphQL"),
    "FashionFinder": ("rank",
        "Visual search for fashion: CLIP and ResNet18 embeddings indexed in FAISS for Pinterest-style similarity search. Live demo.",
        "CLIP · FAISS · PyTorch"),
    # Healthcare
    "Esophageal-Cancer-Detection": ("health",
        "Multi-task EfficientNet-B3 that flags gastrointestinal abnormalities in endoscopy images in real time.",
        "EfficientNet-B3 · PyTorch"),
    "AI-Powered-Multi-Disease-Health-Risk-Prediction": ("health",
        "Screens 17 chronic and genetic conditions from clinical data and chest X-rays. 87.3% average test accuracy.",
        "EfficientNetB0 · TensorFlow"),
    "Heart_disease_linear-regression": ("health",
        "Heart-disease prediction with PCA and logistic regression on clinical features.",
        "scikit-learn"),
    "Alcohol_prediction": ("health",
        "Predicts alcohol use from personality and demographic traits on the UCI drug-consumption data with XGBoost and random forests.",
        "XGBoost · scikit-learn"),
    # Speech & vision
    "noise-robust-kws-distress-detection": ("signal",
        "Distress keyword spotting in noisy cabin audio. 77.0% accuracy at 0 dB SNR from a 0.43 MB model.",
        "MFCC · CNN · PyTorch"),
    "ASL-Alphabet-Recognition_A-Z_-Real-Time-Webcam-CNN": ("signal",
        "Real-time ASL fingerspelling recognition, A to Z, from a webcam feed.",
        "TensorFlow · OpenCV"),
    "Sign-Language-Regonization-using-CNN-Algorithm-with-Meachine-Learning-Techniques-Paper": ("signal",
        "Research paper: a CNN and LSTM pipeline that translates sign-language video into text and audio.",
        "Research paper"),
    "Image-Classification-using-CNN": ("signal",
        "CNN image classifier trained on CIFAR-10.",
        "TensorFlow · Keras"),
    # Finance
    "ATLAS": ("finance",
        "ATLAS-Σ: research simulator for financial infrastructure, modelling institutions, payment obligations, settlement and disruptions.",
        "Python 3.12"),
    "stock-forecasting-aapl-LSTM-RAG": ("finance",
        "AAPL forecasting with LSTM and baselines, plus a strictly grounded RAG copilot. MAPE 3.34%, 0% hallucination.",
        "LSTM · ChromaDB · FastAPI"),
    "Forecasting-and-Predicting-of-stock-using-LSTM-algorithm-using-Machine-Learning-": ("finance",
        "Stock-price forecasting with an LSTM network.",
        "LSTM · Python"),
    # Classical ML
    "Wine-Quality-using-Neural-Networks": ("ml",
        "Neural network written from scratch in NumPy that grades red-wine quality on the UCI dataset.",
        "NumPy"),
    "Student-Performance-Using-Neural-Network": ("ml",
        "Neural-network classifier that predicts student performance bands.",
        "TensorFlow · Keras"),
    "Bayesian-Network-Inference-Problem": ("ml",
        "Bayesian network with exact inference by variable elimination.",
        "pgmpy"),
    # Software & web apps
    "AkilanPortfolio": ("apps",
        "AkilanFlix: Netflix-style AI/ML portfolio site with live search, carousels and a built-in chatbot.",
        "Nuxt · TypeScript · Tailwind"),
    "Pharmacy-management-system": ("apps",
        "Pharmacy operations system: inventory, suppliers, sales and prescriptions through a CLI and a FastAPI REST API.",
        "Python · SQLite · FastAPI"),
    "Library-Management-System-in-Python": ("apps",
        "Library management CLI with multi-copy inventory, borrowers and loans.",
        "Python · SQLite"),
    "Android-App-for-Recycling-and-Donation-app": ("apps",
        "Android app that connects people with recycling centres and donation drives.",
        "Java · Android"),
    # Forks
    "nuscenes-devkit": ("forks", "Fork of the nuScenes devkit, used across the BEV perception work.", "Python · nuScenes"),
    "Opendrivefm-1": ("forks", "Mirror of OpenDriveFM, the camera-only BEV perception system.", "PyTorch · nuScenes"),
    "neurapilot": ("forks", "NeuraPilot: compound AI tutor with LangGraph routing, semantic caching and observability.", "LangGraph · Ollama"),
    "light-show": ("forks", "Fork of Tesla's light-show guide for custom xLights shows on Tesla vehicles.", "xLights"),
    "vehicle-command": ("forks", "Fork of Tesla's Vehicle Command SDK for authenticated vehicle commands.", "Go"),
}

# Keyword rules for repos not in CURATED. Topics count 3x, the repo name 2x, the GitHub
# description 2x and the README 1x (capped), so a short README cannot drown the name.
RULES = {
    "av": ["bev", "nuscenes", "waymo", "carla", "autonom", "self-driving", "driving", "lidar",
           "occupancy", "trajectory", "adas", "vehicle", "traffic", "truck", "slam", "lane",
           "perception", "nuplan", "kitti", "pointpillars", "bevformer", "robotaxi", "motion-planning"],
    "agentic": ["agent", "agents", "agentic", "llm", "llms", "rag", "langgraph", "langchain", "copilot",
                "gpt", "chatbot", "openai", "ollama", "prompt", "genai", "generative", "claude",
                "anthropic", "mcp", "tutor", "workflow"],
    "rank": ["recommend", "recommender", "recsys", "ranker", "ranking", "retrieval", "search",
             "faiss", "embedding", "embeddings", "als", "similarity", "vector", "bandit", "ctr"],
    "health": ["health", "healthcare", "cancer", "disease", "medical", "clinical", "heart", "patient",
               "biobert", "biomedical", "diabetes", "ecg", "eeg", "radiology", "tumor", "covid",
               "drug", "endoscop", "x-ray", "xray", "hospital"],
    "signal": ["speech", "audio", "kws", "keyword", "asl", "sign", "image", "images", "cnn", "vision",
               "webcam", "ocr", "gesture", "detection", "segmentation", "opencv", "yolo", "voice",
               "spectrogram", "cifar"],
    "finance": ["stock", "stocks", "finance", "financial", "fintech", "trading", "trade", "quant",
                "market", "markets", "portfolio-optimization", "payment", "payments", "settlement",
                "bank", "banking", "credit", "fraud", "crypto", "forex", "risk", "aapl", "ticker",
                "options", "hedge"],
    "ml": ["regression", "classifier", "bayesian", "neural", "xgboost", "random-forest", "svm",
           "kmeans", "clustering", "sklearn", "scikit"],
    "apps": ["management", "system", "app", "android", "ios", "website", "portfolio", "frontend",
             "backend", "crud", "django", "flask", "react", "nuxt", "vue", "sqlite"],
}
MIN_SCORE = 2

# Tech names recognised in a README, in display order, for the stack of a new repo.
TECH = ["PyTorch", "TensorFlow", "Keras", "JAX", "scikit-learn", "XGBoost", "LightGBM", "Spark",
        "LangGraph", "LangChain", "LlamaIndex", "Ollama", "OpenAI", "Claude", "ChromaDB", "FAISS",
        "pgvector", "Supabase", "FastAPI", "Flask", "Django", "Streamlit", "React", "Next.js",
        "Vue", "Nuxt", "TypeScript", "Docker", "Kubernetes", "TensorRT", "ONNX", "OpenCV",
        "CARLA", "nuScenes", "ROS", "C++",
        "PostgreSQL", "SQLite", "Redis", "Kafka", "Prometheus", "GraphQL"]

LANG_LABEL = {"Jupyter Notebook": "Notebook", "HTML": "HTML / JS"}


def tokens(text):
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text or "")
    return [t for t in re.split(r"[^a-z0-9]+", text.lower()) if t]


def _score(toks, words):
    hits = 0
    for w in words:
        if "-" in w:  # phrase: match on the joined text
            hits += " ".join(toks).count(w.replace("-", " "))
        elif len(w) <= 4:
            hits += toks.count(w)
        else:
            hits += sum(1 for t in toks if t.startswith(w))
    return hits


def hidden(repo, user):
    if repo["name"] in HIDE or repo["name"].lower() == user.lower():
        return True
    # Empty repos: nothing pushed beyond an initial commit.
    return (repo.get("size") or 0) == 0 and repo["name"] not in CURATED


def classify(repo, readme=""):
    name = repo["name"]
    if name in CURATED:
        return CURATED[name][0]
    if repo.get("fork"):
        return "forks"
    parts = [
        (tokens(" ".join(repo.get("topics") or [])), 3, None),
        (tokens(name), 2, None),
        (tokens(repo.get("description") or ""), 2, None),
        (tokens(readme[:6000]), 1, 6),
    ]
    best, best_score = "ml", 0
    for domain, words in RULES.items():
        sc = 0
        for toks, weight, cap in parts:
            s = _score(toks, words)
            sc += weight * (min(s, cap) if cap else s)
        if sc > best_score:
            best, best_score = domain, sc
    if best_score >= MIN_SCORE:
        return best
    return "apps" if (repo.get("language") or "") in ("JavaScript", "TypeScript", "Vue", "HTML", "Java", "Kotlin", "Swift") else "ml"


# ----------------------------------------------------------------- descriptions

_SKIP = re.compile(r"^(built by|made by|author|live demo|demo|table of contents|contents|license|"
                   r"installation|getting started|setup|usage|requirements|contribution:|status|"
                   r"note|warning|disclaimer|academic project|welcome|this is a research prototype)", re.I)


def _clean_md(line):
    line = re.sub(r"<[^>]+>", " ", line)                    # html
    line = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", line)       # images
    line = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", line)    # links -> text
    line = re.sub(r"[*_`~]+", "", line)                     # emphasis
    line = re.sub(r"^\s*(#+|>+|[-+*]|\d+\.)\s*", "", line)  # heading / quote / bullet
    line = re.sub(r"&nbsp;|&amp;", " ", line)
    line = re.sub(r"[\U0001F000-\U0001FAFF☀-➿️]", "", line)  # emoji
    return re.sub(r"\s+", " ", line).strip(" -|·•")


def description_from_readme(readme, name=""):
    """First sentence of the README that actually describes the project."""
    if not readme:
        return ""
    in_code = False
    title = _clean_md(name.replace("-", " ").replace("_", " ")).lower()
    for raw in readme.splitlines():
        if raw.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code or raw.strip().startswith("|") or "shields.io" in raw or '="' in raw or "http" in raw:
            continue
        line = _clean_md(raw)
        words = line.split()
        if len(words) < 6 or _SKIP.match(line) or line.lower() == title:
            continue
        if sum(c.isalpha() for c in line) < 0.6 * len(line):
            continue  # ascii art, tables, dates
        sent = re.split(r"(?<=[.!?])\s+", line)[0]
        if len(sent.split()) < 6:
            sent = line
        sent = sent.rstrip(" :")
        if len(sent) > 150:
            sent = sent[:147].rsplit(" ", 1)[0] + "…"
        return sent[0].upper() + sent[1:]
    return ""


def stack_from_readme(readme, language):
    found = []
    low = readme.lower() if readme else ""
    for t in TECH:
        pat = r"(?<![a-z0-9])" + re.escape(t.lower()) + r"(?![a-z0-9])"
        if low and re.search(pat, low):
            found.append(t)
        if len(found) == 3:
            break
    lang = LANG_LABEL.get(language or "", language or "")
    if lang and lang not in found:
        found = [lang] + found[:2]
    return " · ".join(found) if found else "Documentation"


def humanise(name):
    words = re.sub(r"[-_]+", " ", name).strip()
    return words[0].upper() + words[1:] if words else name


def describe(repo, readme=""):
    """(description, stack) for any repo, never blank."""
    name = repo["name"]
    if name in CURATED:
        return CURATED[name][1], CURATED[name][2]
    desc = (repo.get("description") or "").strip() or description_from_readme(readme, name)
    if not desc:
        desc = f"{humanise(name)}."
    return desc, stack_from_readme(readme, repo.get("language"))
