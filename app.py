from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from serpapi import GoogleSearch
import logging
import time
import os
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()
app = FastAPI()

# Enable logging to debug API calls
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Allow frontend (JS) to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change "*" to your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SERPAPI_KEY = os.getenv("SERPAPI_KEY")

def get_nearby_restaurants(lat, lon, radius=2000, limit=10):
    """
    Step 1: Get nearby restaurants from Google Maps
    """
    params = {
        "engine": "google_maps",
        "q": "restaurants",
        "ll": f"@{lat},{lon},14z",
        "type": "search",
        "api_key": SERPAPI_KEY
    }
    
    logger.info(f"Searching restaurants near {lat}, {lon}")
    search = GoogleSearch(params)
    results = search.get_dict()
    
    # Check for errors
    if "error" in results:
        logger.error(f"SerpAPI error: {results['error']}")
        return []
    
    local_results = results.get("local_results", [])
    logger.info(f"Found {len(local_results)} restaurants from Google Maps")
    
    restaurants = []
    for i, r in enumerate(local_results[:limit]):
        try:
            restaurant_data = {
                "name": r.get("title"),
                "address": r.get("address"),
                "rating": r.get("rating"),
                "reviews_count": r.get("reviews"),
                "phone": r.get("phone"),
                "website": r.get("links", {}).get("website") if r.get("links") else None,
                "place_id": r.get("place_id"),
                "data_id": r.get("data_id"),
                "data_cid": r.get("data_cid"),
                "gps_coordinates": r.get("gps_coordinates", {}),
                "thumbnail": r.get("thumbnail"),
                "type": r.get("type"),
                "hours": r.get("hours"),
                "service_options": r.get("service_options", {}),
                "reviews": []  # Will be populated by get_restaurant_reviews
            }
            
            # Get reviews for this restaurant
            place_id = r.get("place_id") or r.get("data_cid")
            if place_id:
                logger.info(f"Getting reviews for restaurant: {restaurant_data['name']}")
                reviews = get_restaurant_reviews(place_id)
                restaurant_data["reviews"] = reviews
                
                # Add small delay to avoid rate limiting
                time.sleep(0.5)
            
            restaurants.append(restaurant_data)
            
        except Exception as e:
            logger.warning(f"Error processing restaurant {i}: {str(e)}")
            continue
    
    return restaurants


def get_restaurant_reviews(place_id):
    """
    Step 2: Get top 10 reviews for each restaurant using Google Maps Reviews API
    """
    try:
        # Try with place_id first
        params = {
            "engine": "google_maps_reviews",
            "place_id": place_id,
            "sort_by": "most_relevant",  # or "newest", "highest_rating", "lowest_rating"
            "api_key": SERPAPI_KEY
        }
        
        search = GoogleSearch(params)
        results = search.get_dict()
        
        # Check for errors
        if "error" in results:
            logger.warning(f"Reviews API error for place_id {place_id}: {results['error']}")
            
            # If place_id fails, try with data_cid using different approach
            return get_reviews_from_place_results(place_id)
        
        reviews_data = results.get("reviews", [])
        logger.info(f"Found {len(reviews_data)} reviews for place_id: {place_id}")
        
        # Extract top 10 reviews with detailed information
        reviews = []
        for review in reviews_data[:10]:
            try:
                review_info = {
                    "author": review.get("user", {}).get("name", "Anonymous"),
                    "author_reviews_count": review.get("user", {}).get("reviews", 0),
                    "rating": review.get("rating", 0),
                    "text": review.get("snippet", ""),
                    "date": review.get("date", ""),
                    "likes": review.get("likes", 0),
                    "images": review.get("images", []),
                    "response_from_owner": review.get("response_from_owner", {})
                }
                reviews.append(review_info)
            except Exception as e:
                logger.warning(f"Error processing review: {str(e)}")
                continue
        
        return reviews
        
    except Exception as e:
        logger.error(f"Error getting reviews for place_id {place_id}: {str(e)}")
        return []


def get_reviews_from_place_results(data_cid):
    """
    Alternative method: Get reviews using Google Maps Place Results API
    """
    try:
        params = {
            "engine": "google_maps",
            "place_id": data_cid,
            "api_key": SERPAPI_KEY
        }
        
        search = GoogleSearch(params)
        results = search.get_dict()
        
        place_results = results.get("place_results", {})
        reviews_data = place_results.get("user_reviews", {}).get("most_relevant", [])
        
        logger.info(f"Found {len(reviews_data)} reviews using place results for: {data_cid}")
        
        reviews = []
        for review in reviews_data[:10]:
            try:
                review_info = {
                    "author": review.get("user", "Anonymous"),
                    "rating": review.get("rating", 0),
                    "text": review.get("snippet", ""),
                    "date": review.get("date", ""),
                    "likes": review.get("likes", 0)
                }
                reviews.append(review_info)
            except Exception as e:
                logger.warning(f"Error processing review from place results: {str(e)}")
                continue
        
        return reviews
        
    except Exception as e:
        logger.error(f"Error with place results method: {str(e)}")
        return []


def calculate_personalized_score(restaurant, user_preferences=None):
    """
    Step 3: AI-based scoring for personalized recommendations
    This will analyze reviews and match with user preferences
    """
    if not user_preferences:
        # Default scoring based on rating and review count
        rating = restaurant.get("rating", 0)
        reviews_count = restaurant.get("reviews_count", 0)
        
        # Basic scoring algorithm
        base_score = rating * 2  # Max 10 points from rating
        popularity_bonus = min(reviews_count / 100, 2)  # Max 2 points from popularity
        
        return round(base_score + popularity_bonus, 1)
    
    # TODO: Implement AI-based taste matching using reviews
    # This will analyze review text for taste preferences like:
    # - Spicy food preferences
    # - North Indian vs South Indian
    # - Veg vs Non-veg
    # - Price sensitivity
    # - Ambiance preferences
    
    return restaurant.get("rating", 0) * 2


@app.get("/restaurants")
def restaurants(lat: float, lon: float, radius: int = 2000, limit: int = 10):
    """
    Get nearby restaurants with reviews for personalized recommendations
    """
    try:
        restaurants_data = get_nearby_restaurants(lat, lon, radius, limit)
        
        # Add personalized scoring
        for restaurant in restaurants_data:
            restaurant["lokal_score"] = calculate_personalized_score(restaurant)
            restaurant["total_reviews_text"] = len([r for r in restaurant.get("reviews", []) if r.get("text")])
        
        # Sort by Lokal score (highest first)
        restaurants_data.sort(key=lambda x: x.get("lokal_score", 0), reverse=True)
        
        return {
            "success": True,
            "latitude": lat,
            "longitude": lon,
            "radius": radius,
            "count": len(restaurants_data),
            "restaurants": restaurants_data,
            "summary": {
                "total_restaurants": len(restaurants_data),
                "total_reviews_collected": sum(len(r.get("reviews", [])) for r in restaurants_data),
                "average_rating": round(sum(r.get("rating", 0) for r in restaurants_data if r.get("rating")) / len([r for r in restaurants_data if r.get("rating")]), 2) if restaurants_data else 0
            }
        }
        
    except Exception as e:
        logger.error(f"Error in restaurants endpoint: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "latitude": lat,
            "longitude": lon,
            "restaurants": []
        }


@app.get("/")
def read_root():
    return {
        "message": "🏠 Lokal Restaurant Finder API",
        "description": "Get nearby restaurants with reviews for AI-powered personalized recommendations",
        "endpoints": {
            "/restaurants": "Get nearby restaurants with detailed reviews"
        },
        "example": "/restaurants?lat=17.3850&lon=78.4867&limit=5",
        "features": [
            "✅ Nearby restaurant discovery",
            "✅ Top 10 reviews per restaurant", 
            "✅ Detailed restaurant information",
            "🔄 AI personalization scoring (basic)",
            "🔄 Taste preference matching (coming soon)"
        ]
    }


@app.get("/test")
def test_serpapi():
    """
    Test endpoint to verify SerpAPI is working
    """
    try:
        # Test search
        params = {
            "engine": "google_maps",
            "q": "restaurants in Hyderabad",
            "api_key": SERPAPI_KEY
        }
        
        search = GoogleSearch(params)
        results = search.get_dict()
        
        return {
            "serpapi_working": "error" not in results,
            "search_results_count": len(results.get("local_results", [])),
            "api_key_valid": True if "local_results" in results else False
        }
        
    except Exception as e:
        return {
            "serpapi_working": False,
            "error": str(e),
            "api_key_valid": False
        }