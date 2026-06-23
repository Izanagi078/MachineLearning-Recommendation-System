import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def test_api():
    print("=== RUNNING API ENDPOINT TESTS ===")
    
    # 1. Test GET /api/stats
    print("\n1. Testing GET /api/stats...")
    res = requests.get(f"{BASE_URL}/api/stats")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert "total_ratings" in data, "Missing ratings count"
    assert "metrics" in data, "Missing metrics metadata"
    print(f"[OK] Stats check passed. Total Ratings: {data['total_ratings']}, RMSE: {data['metrics']['rmse']:.4f}")

    # 2. Test POST /api/onboarding
    print("\n2. Testing POST /api/onboarding...")
    payload = {
        "genres": ["Sci-Fi", "Adventure"],
        "keywords": "time travel space"
    }
    res = requests.post(f"{BASE_URL}/api/onboarding", json=payload)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert "userId" in data, "Missing userId in onboarding response"
    assert "matched_movies" in data, "Missing matched_movies"
    guest_id = data["userId"]
    print(f"[OK] Onboarding passed. Generated Guest User ID: {guest_id}")
    print(f"     Matched Movies: {[m['title'] for m in data['matched_movies']]}")

    # 3. Test GET /api/recommendations
    print("\n3. Testing GET /api/recommendations...")
    res = requests.get(f"{BASE_URL}/api/recommendations?userId={guest_id}&weight_collaborative=0.5")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    recs = res.json()
    assert len(recs) > 0, "Recommendations list is empty"
    assert "explanation" in recs[0], "Missing XAI explanation block"
    print(f"[OK] Recommendations passed. Received {len(recs)} personalized items.")

    # 4. Test POST /api/ratings (User Interaction & Online SVD Update)
    print("\n4. Testing POST /api/ratings (Online SGD step)...")
    target_movie = recs[0]["movieId"]
    payload_rating = {
        "userId": guest_id,
        "movieId": target_movie,
        "rating": 5.0
    }
    res = requests.post(f"{BASE_URL}/api/ratings", json=payload_rating)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    print(f"[OK] Rating submission processed successfully.")

    # 5. Test GET /api/feed
    print("\n5. Testing GET /api/feed (Network Feed)...")
    res = requests.get(f"{BASE_URL}/api/feed")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    feed = res.json()
    assert len(feed) > 0, "Feed list is empty"
    # The last rating we submitted should be first in the feed
    assert feed[0]["userId"] == guest_id, "Latest user interaction mismatch in feed"
    print(f"[OK] Global network feed verified. Last action: User {feed[0]['userId']} rated movie {feed[0]['movieId']} ({feed[0]['title']}).")

    print("\n=== ALL FastAPI ENDPOINT INTEGRATION TESTS PASSED ===")

if __name__ == "__main__":
    # Wait for server to be fully active
    time.sleep(2)
    try:
        test_api()
    except Exception as e:
        print(f"[ERROR] API test failed: {e}")
        exit(1)
