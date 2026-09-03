import stripe
from decouple import config

stripe.api_key = config("STRIPE_SECRET_KEY")

payment_intent_id = "pi_3TzVt5DYwj4HOWCo19Zgh5QQ"

confirmed = stripe.PaymentIntent.confirm(payment_intent_id,
                                         payment_method="pm_card_visa",)

print("Status:", confirmed["status"])