import stripe
import os
import sys
import logging

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../LogicHive-Hub-Private/backend")))

from core.config import get_setting

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load Stripe Key
STRIPE_API_KEY = get_setting("STRIPE_API_KEY")
stripe.api_key = STRIPE_API_KEY

def calibrate():
    if not stripe.api_key:
        logger.error("Stripe API Key missing. Cannot calibrate.")
        return

    logger.info("Starting Stripe Calibration...")
    
    try:
        # 1. List Products
        products = stripe.Product.list(active=True, limit=10)
        found_prices = {}
        
        for product in products.data:
            logger.info(f"Product Found: {product.name} ({product.id})")
            # Get Prices for this product
            prices = stripe.Price.list(product=product.id, active=True, limit=5)
            for price in prices.data:
                logger.info(f"  - Price Found: {price.id} | currency: {price.currency} | amount: {price.unit_amount}")
                # Simple heuristic mapping
                if "basic" in product.name.lower():
                    found_prices["basic"] = price.id
                elif "pro" in product.name.lower():
                    found_prices["pro"] = price.id

        if found_prices:
            logger.info("\n--- Recommended PLAN_LIMITS Configuration ---")
            print("PLAN_LIMITS = {")
            for name, p_id in found_prices.items():
                limit = 1000 if name == "basic" else 10000
                print(f"    '{p_id}': {{'limit': {limit}, 'name': '{name}'}},")
            print("}")
            logger.info("\nPlease update LogicHive-Hub-Private/backend/hub/stripe_api.py with these IDs.")
        else:
            logger.warning("No LogicHive-related products found in Stripe Dashboard (Names should include 'basic' or 'pro').")
            logger.info("Please create Products in Stripe Sandbox named 'LogicHive Basic' and 'LogicHive Pro'.")

    except Exception as e:
        logger.error(f"Stripe Calibration Error: {e}")

if __name__ == "__main__":
    calibrate()
