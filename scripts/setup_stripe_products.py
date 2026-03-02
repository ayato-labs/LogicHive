import stripe
import os
import sys
import logging
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../LogicHive-Hub-Private/backend")))

# Load .env
load_dotenv("LogicHive-Hub-Private/backend/.env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load Stripe Key
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")
stripe.api_key = STRIPE_API_KEY

def setup_products():
    if not stripe.api_key:
        logger.error("Stripe API Key missing in .env. Please set STRIPE_API_KEY first.")
        return

    products_to_create = [
        {
            "name": "LogicHive Basic",
            "description": "Base plan for small teams (1,000 requests/mo)",
            "amount": 1000, # 1,000 JPY
            "currency": "jpy",
            "interval": "month"
        },
        {
            "name": "LogicHive Pro",
            "description": "Advanced plan for larger enterprises (10,000 requests/mo)",
            "amount": 10000, # 10,000 JPY
            "currency": "jpy",
            "interval": "month"
        }
    ]

    found_prices = {}

    for p_def in products_to_create:
        try:
            # Check if exists
            existing = stripe.Product.list(limit=10)
            product = next((p for p in existing.data if p.name == p_def["name"]), None)

            if not product:
                logger.info(f"Creating product: {p_def['name']}...")
                product = stripe.Product.create(
                    name=p_def["name"],
                    description=p_def["description"]
                )
            
            # Check for existing prices
            prices = stripe.Price.list(product=product.id, active=True, limit=1)
            if not prices.data:
                logger.info(f"Creating price for {p_def['name']}...")
                price = stripe.Price.create(
                    unit_amount=p_def["amount"],
                    currency=p_def["currency"],
                    recurring={"interval": p_def["interval"]},
                    product=product.id,
                )
            else:
                price = prices.data[0]
            
            logger.info(f"SUCCESS: {p_def['name']} -> Price ID: {price.id}")
            found_prices[p_def["name"]] = price.id

        except Exception as e:
            logger.error(f"Error setting up {p_def['name']}: {e}")

    if found_prices:
        logger.info("\n--- UPDATED CONFIGURATION ---")
        print("Please copy these IDs into LogicHive-Hub-Private/backend/hub/stripe_api.py:")
        print("PLAN_LIMITS = {")
        for name, p_id in found_prices.items():
            limit = 1000 if "Basic" in name else 10000
            print(f"    '{p_id}': {{'limit': {limit}, 'name': '{name.lower().replace('logichive ', '')}'}},")
        print("}")

if __name__ == "__main__":
    setup_products()
