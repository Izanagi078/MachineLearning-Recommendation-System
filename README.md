# Hybrid Movie Recommender Engine with Dynamic Cold-Start Resolution

An advanced, production-grade **Hybrid Machine Learning Recommendation System** combining Collaborative Filtering (Matrix Factorization via SVD) and Content-Based NLP Filtering (TF-IDF + Cosine Similarity) using the MovieLens-Latest-Small dataset (100,000 ratings).

This project implements advanced engineering practices to solve the standard limitations of retail recommenders, specifically addressing **Cold-Start (Onboarding Mode)**, **Explaining Predictions (XAI)**, and **Multi-Metric Search Optimization** (Diversity vs. Novelty).

---

## 🌟 Key Features

1. **Latent Matrix Factorization SVD**:
   * Centered SVD using `scikit-learn`'s `TruncatedSVD` on the centered user-movie rating pivot table, predicting missing ratings based on hidden latent preferences.
   * Incorporates **Temporal Decay Weighting** ($e^{-\lambda t}$) to discount old ratings, making recommendations favor recent tastes.
2. **Tag-Augmented NLP Content-Based Engine**:
   * Aggregates user-generated tags, movie titles, and pipe-separated genres into a single content document per movie.
   * Uses `TfidfVectorizer` and linear similarity kernels to match user profile text vectors against candidates.
3. **True Cold-Start Onboarding Sandbox**:
   * If a user is completely new, the UI launches a dynamic onboarding card to collect preferred genres and keywords.
   * Instantly builds a user profile vector in the TF-IDF space and calculates recommendations using Cosine Similarity.
4. **Dynamic Active Session Queue**:
   * Users can click "Like" or "Dislike" directly on recommended movie cards in the Streamlit UI to dynamically adjust their profile vector and re-rank suggestions in real-time.
5. **Multi-Metric Search Optimization**:
   * **Novelty Slider (Hidden Gems)**: Adjusts penalty on globally popular blockbusters to highlight highly-rated lesser-known movies.
   * **Diversity Slider (Genre Coverage)**: Implements a greedy re-ranking genre penalty (MMR-style) to ensure recommended lists span multiple movie categories.
6. **Explainable AI (XAI) Panel**:
   * Every recommended movie contains a detailed explanation panel. It outlines why it was recommended, showing either the latent factor similarity to a historically liked movie or the overlapping keywords in the TF-IDF space.

---

## 📁 Repository Structure

```text
movie_recommender_ml/
│
├── data/                    # GroupLens MovieLens-Latest-Small dataset
│
├── src/
│   ├── __init__.py
│   ├── data_loader.py       # Downloads, unzips, aggregates tags, and builds text corpus
│   ├── models.py            # SVD, TF-IDF, HybridRecommender, and XAI Explanations
│   ├── evaluation.py        # Ranking validation metrics (RMSE, MAP@K, NDCG@K)
│   └── train.py             # Offline training pipeline and model serialization (.pkl)
│
├── app/
│   └── dashboard.py         # Streamlit visual interface
│
├── requirements.txt         # Package dependencies
├── test_pipeline.py         # Automated integration and math validation tests
└── README.md                # Project documentation
```

---

## 🚀 Installation and Run Guide

### 1. Set Up Python Dependencies
Ensure you have the required packages installed in your environment:
```bash
pip install -r requirements.txt
```

### 2. Run the Offline Training and Evaluation
Train the collaborative SVD and TF-IDF models, run the test-split validation metrics, and serialize the models:
```bash
python -m src.train
```

*This will output the test metrics (RMSE, MAP@10, NDCG@10) and save model files to the `models/` cache folder.*

### 3. Launch the Interactive Dashboard
Run the Streamlit app:
```bash
streamlit run app/dashboard.py
```

*Open `http://localhost:8501` in your browser to interact with the dashboard.*

---

## 📊 Evaluation & Mathematical Validation

The training script validates the models on an 80/20 train-test split, outputting:
* **RMSE / MAE**: SVD rating prediction accuracy (Standard: `~0.93` RMSE).
* **Mean Average Precision (MAP@10)**: Measures the relevance of recommended movies.
* **Normalized Discounted Cumulative Gain (NDCG@10)**: Evaluates the system's ability to rank highly relevant movies at the top of the recommended list.
