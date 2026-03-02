import stripe
import os
from dotenv import load_dotenv

load_dotenv()
stripe.api_key = os.getenv("STRIPE_API_KEY")

def setup_stripe_plans():
    print("--- Setting up LogicHive Stripe Plans ---")
    
    # 1. Basic Plan (e.g., $29/mo)
    basic_product = stripe.Product.create(name="LogicHive Basic", description="Small teams, 1k requests/mo")
    basic_price = stripe.Price.create(
        product=basic_product.id,
        unit_amount=2900,
        currency="usd",
        recurring={"interval": "month"}
    )
    print(f"Basic Plan Created: {basic_price.id}")
    
    # 2. Pro Plan (e.g., $99/mo)
    pro_product = stripe.Product.create(name="LogicHive Pro", description="Enterprise, 10k requests/mo")
    pro_price = stripe.Price.create(
        product=pro_product.id,
        unit_amount=9900,
        currency="usd",
        recurring={"interval": "month"}
    )
    print(f"Pro Plan Created: {pro_price.id}")
    
    print("\nSAVE THESE PRICE IDs in your .env or settings!")

if __name__ == "__main__":
    setup_stripe_plans()
