# Clerk.com Monetization Implementation Plan

## Overview
Integrate Clerk.com for authentication and Stripe for credit-based monetization of YouTube StudyBuddy. This plan prioritizes rapid deployment with minimal custom code.

## Prerequisites
- Clerk account (free tier available)
- Stripe account
- EC2 instance with domain configured

## Architecture

```
User → Clerk Auth Widget → Streamlit App → Credit Check → Process Video → Deduct Credits
                ↓                                ↓
         Clerk Backend                    Stripe Webhooks
                ↓                                ↓
         User Metadata                    Update Credits
```

## Implementation Steps

### Phase 1: Clerk Setup (1-2 hours)

**1.1 Create Clerk Application**
- Sign up at clerk.com
- Create new application
- Enable Google OAuth provider
- Note: Application ID, Publishable Key, Secret Key

**1.2 Install Dependencies**
```bash
cd ytstudybuddy
uv add clerk-sdk-python streamlit-clerk
```

**1.3 Configure Environment**
Add to `.env`:
```
CLERK_PUBLISHABLE_KEY=pk_...
CLERK_SECRET_KEY=sk_...
STRIPE_SECRET_KEY=sk_...
STRIPE_PUBLISHABLE_KEY=pk_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### Phase 2: Streamlit Integration (2 hours)

**2.1 Add Authentication Wrapper**
Create `src/auth.py`:
```python
from clerk_sdk import Clerk
import streamlit as st

clerk = Clerk(api_key=os.getenv("CLERK_SECRET_KEY"))

def require_auth():
    """Protect pages with Clerk authentication"""
    # Check session token from Clerk component
    # Return user object with credits
    pass

def get_user_credits(user_id):
    """Fetch credits from Clerk user metadata"""
    user = clerk.users.get(user_id)
    return user.public_metadata.get("credits", 0)

def deduct_credits(user_id, amount):
    """Deduct credits after successful processing"""
    pass
```

**2.2 Update Streamlit App**
Modify `streamlit_app.py`:
```python
import streamlit as st
from src.auth import require_auth, get_user_credits, deduct_credits

# Add Clerk component at top
st.markdown("""
<script async src="https://[your-clerk-domain].clerk.accounts.dev/npm/@clerk/clerk-js@latest/dist/clerk.browser.js"></script>
<clerk-signin-button></clerk-signin-button>
""", unsafe_allow_html=True)

user = require_auth()  # Protect entire app
st.sidebar.write(f"Credits: {get_user_credits(user.id)}")

# Before processing video
if credits < 5:
    st.error("Insufficient credits. Purchase more below.")
    show_stripe_checkout()
else:
    # Process video
    deduct_credits(user.id, 5)
```

### Phase 3: Stripe Integration (1-2 hours)

**3.1 Create Credit Packages**
In Stripe Dashboard:
- Product: "50 Credits" → Price: $5.00
- Product: "100 Credits" → Price: $9.00
- Product: "500 Credits" → Price: $40.00

**3.2 Add Checkout Flow**
Create `src/payments.py`:
```python
import stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

def create_checkout_session(user_id, package="50_credits"):
    """Create Stripe Checkout session"""
    prices = {
        "50_credits": "price_...",
        "100_credits": "price_...",
        "500_credits": "price_...",
    }

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price": prices[package], "quantity": 1}],
        mode="payment",
        success_url="https://your-domain.com/success",
        cancel_url="https://your-domain.com/cancel",
        client_reference_id=user_id,
        metadata={"package": package}
    )
    return session.url
```

**3.3 Setup Webhook Handler**
Create FastAPI endpoint `src/webhook.py`:
```python
from fastapi import FastAPI, Request
from clerk_sdk import Clerk
import stripe

app = FastAPI()
clerk = Clerk(api_key=os.getenv("CLERK_SECRET_KEY"))

@app.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle successful payments"""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    event = stripe.Webhook.construct_event(
        payload, sig_header, os.getenv("STRIPE_WEBHOOK_SECRET")
    )

    if event.type == "checkout.session.completed":
        session = event.data.object
        user_id = session.client_reference_id
        package = session.metadata.package

        # Add credits to Clerk user metadata
        credits_to_add = {"50_credits": 50, "100_credits": 100, "500_credits": 500}
        user = clerk.users.get(user_id)
        current_credits = user.public_metadata.get("credits", 0)

        clerk.users.update(user_id, {
            "public_metadata": {
                "credits": current_credits + credits_to_add[package]
            }
        })

    return {"status": "success"}
```

Run webhook server:
```bash
uv run uvicorn src.webhook:app --port 8001
```

### Phase 4: Deployment (1 hour)

**4.1 Update EC2 Configuration**
```bash
# Install nginx for reverse proxy
sudo apt install nginx

# Configure nginx to route:
# - / → Streamlit (port 8501)
# - /webhook/stripe → FastAPI (port 8001)
```

**4.2 Register Stripe Webhook**
In Stripe Dashboard:
- Add endpoint: `https://your-domain.com/webhook/stripe`
- Select event: `checkout.session.completed`
- Copy webhook secret to `.env`

**4.3 Configure Clerk Production**
- Add production domain to Clerk dashboard
- Update CORS settings
- Deploy Clerk components with production keys

### Phase 5: Testing (30 min)

**5.1 Test Flow**
1. Visit app → Clerk login appears
2. Login with Google
3. Check credits = 0
4. Click "Buy Credits" → Stripe Checkout
5. Complete test payment (use Stripe test cards)
6. Verify credits added to account
7. Process video → credits deducted
8. Verify credit balance updates

**5.2 Test Webhook**
```bash
stripe listen --forward-to localhost:8001/webhook/stripe
stripe trigger checkout.session.completed
```

## Credit Pricing Model

**Costs per video:**
- Claude API: $0.01-0.05
- Server: $0.001-0.01
- Total: ~$0.02-0.06

**Revenue model:**
- 1 credit = $0.10
- 1 video = 5 credits ($0.50)
- Profit margin: ~88%

**Packages:**
- $5 = 50 credits (10 videos)
- $9 = 100 credits (20 videos) - 10% bonus
- $40 = 500 credits (100 videos) - 20% bonus

## Alternative: Clerk + Stripe No-Code

If coding webhook handler is too complex, use Clerk's built-in Stripe integration:
1. Connect Stripe in Clerk Dashboard
2. Use Clerk's subscription management (no webhook code needed)
3. Trade-off: Less flexibility, but 30-minute setup

## Timeline

- **Day 1 Morning**: Clerk setup + Streamlit integration (3 hours)
- **Day 1 Afternoon**: Stripe integration + webhook (2 hours)
- **Day 2 Morning**: Deployment + testing (1.5 hours)
- **Total**: ~6-7 hours spread over 1-2 days

## Rollback Plan

If issues arise:
1. Keep app public without auth temporarily
2. Use API key system (users bring own Claude key)
3. Fall back to donation model

## Next Steps After Launch

1. Add usage analytics dashboard
2. Implement referral credits
3. Add monthly subscription option ($10/month unlimited)
4. Email notifications for low credits

## Resources

- [Clerk Python SDK](https://clerk.com/docs/reference/backend-api)
- [Stripe Checkout](https://stripe.com/docs/payments/checkout)
- [Streamlit + Auth Pattern](https://docs.streamlit.io/knowledge-base/deploy/authentication-without-sso)

---

## Alternative Payment Solutions for South African / International Users

### Problem with Stripe in South Africa
- Limited currency support (ZAR not fully supported for all features)
- High FX conversion fees (3-5% on top of payment processing)
- Complicated multi-currency setup
- Payout delays for non-US accounts

### Better Options for International Payments

#### 1. **BTCPay Server** (Recommended for Bitcoin/Lightning)
**Pros:**
- Self-hosted, no middleman, no fees beyond network costs
- Accept Bitcoin + Lightning Network (instant, near-zero fees)
- Stablecoins via Bitcoin layers (L-BTC, RGB protocol)
- No currency conversion needed - you receive BTC directly
- Perfect for South African sellers (no bank dependencies)

**Implementation:**
```bash
# Install BTCPay Server on EC2
docker run -d -p 80:80 -p 443:443 btcpayserver/btcpayserver

# Python integration
uv add btcpay-python
```

**Integration code:**
```python
from btcpay import BTCPayClient

client = BTCPayClient(host="https://your-btcpay.com", api_key="...")

# Create invoice for 50 credits ($5 worth of BTC)
invoice = client.create_invoice({
    "price": 5.0,
    "currency": "USD",  # Priced in USD, paid in BTC
    "orderId": f"credits_{user_id}",
    "notificationURL": "https://your-app.com/webhook/btcpay"
})

# User pays with Lightning (instant) or on-chain BTC
# Webhook confirms payment → add credits
```

**Timeline:** 4-6 hours setup
**Costs:** Network fees only (Lightning: <$0.01, On-chain: $0.50-2)

---

#### 2. **Coinbase Commerce** (Easiest Crypto Option)
**Pros:**
- Hosted solution (like Stripe for crypto)
- Accept BTC, ETH, USDC, USDT (stablecoins)
- Auto-converts to USD/ZAR if desired
- Simple API, similar to Stripe
- No FX fees if you keep stablecoins

**Implementation:**
```bash
uv add coinbase-commerce
```

```python
from coinbase_commerce import Client

client = Client(api_key="...")

charge = client.charge.create({
    "name": "50 Credits",
    "description": "YouTube StudyBuddy Credits",
    "pricing_type": "fixed_price",
    "local_price": {"amount": "5.00", "currency": "USD"},
    "metadata": {"user_id": user_id, "credits": 50}
})

# User pays with crypto wallet
# Webhook: charge.confirmed → add credits
```

**Timeline:** 2-3 hours setup
**Costs:** 1% fee (much lower than Stripe's 2.9% + $0.30)

---

#### 3. **Strike API** (Lightning Network)
**Pros:**
- Lightning Network payments (instant, <$0.001 fees)
- Auto-converts to USD/ZAR on receipt (optional)
- Great UX for non-crypto users (they can pay with cards, receive BTC)
- Available in South Africa

**Implementation:**
```bash
uv add strike-api
```

**Timeline:** 2-3 hours
**Costs:** 0.3% (lowest fee of all options)

---

#### 4. **OpenNode** (Bitcoin Payment Processor)
**Pros:**
- Accept BTC/Lightning
- Auto-settle to fiat if desired
- Available in 150+ countries including South Africa
- Hosted solution (no infrastructure needed)

**Timeline:** 2-3 hours
**Costs:** 1% fee

---

#### 5. **USDC/USDT Stablecoin Direct** (Most Stable)
**Approach:** Accept stablecoins directly via smart contract

**Pros:**
- No volatility (1 USDC = 1 USD always)
- Near-zero fees on Polygon/Solana (<$0.01)
- No currency conversion
- Easy to cash out on South African exchanges (Luno, VALR)

**Implementation:**
```python
# Use web3.py to monitor wallet address
from web3 import Web3

w3 = Web3(Web3.HTTPProvider("https://polygon-rpc.com"))
usdc_contract = w3.eth.contract(address="0x...", abi=usdc_abi)

# Monitor for incoming USDC payments
# Match payment amounts to credit packages
```

**Setup with Thirdweb (easiest):**
```bash
uv add thirdweb-sdk
```

```python
from thirdweb import ThirdwebSDK

sdk = ThirdwebSDK("polygon")
# Generate payment QR codes for users
# Webhook when USDC received → add credits
```

**Timeline:** 3-4 hours
**Costs:** Network fees only (~$0.01 per transaction on Polygon)

---

### Recommended Stack for South Africa

**Option A: Fast & Simple**
- **Coinbase Commerce** for stablecoin payments
- Accept USDC/USDT (no volatility)
- 1% fee, 2-hour setup
- Cash out on Luno/VALR in ZAR

**Option B: Maximum Control**
- **BTCPay Server** self-hosted
- Lightning Network for instant payments
- Zero middleman fees
- Keep BTC or convert to ZAR on exchanges

**Option C: Hybrid**
- **Strike API** for Lightning (instant + low fees)
- **Coinbase Commerce** for traditional crypto users
- Offer both options on checkout page

---

### Updated Architecture with Crypto Payments

```
User → Clerk Auth → Streamlit App → Choose Payment
                                       ↓
                    ┌──────────────────┼──────────────────┐
                    ↓                  ↓                   ↓
            BTCPay Invoice    Coinbase Commerce    Strike Lightning
                    ↓                  ↓                   ↓
            Lightning Payment    USDC Payment      Instant BTC
                    ↓                  ↓                   ↓
                    └──────────────────┴───────────────────┘
                                       ↓
                                Webhook Handler
                                       ↓
                            Update Credits in Clerk
```

---

### Implementation Example: Coinbase Commerce + Clerk

```python
# src/payments_crypto.py
from coinbase_commerce.client import Client
from coinbase_commerce.webhook import Webhook
import os

client = Client(api_key=os.getenv("COINBASE_COMMERCE_API_KEY"))

def create_crypto_checkout(user_id, package="50_credits"):
    """Create Coinbase Commerce charge"""
    packages = {
        "50_credits": ("50 Credits", 5.00, 50),
        "100_credits": ("100 Credits", 9.00, 100),
        "500_credits": ("500 Credits", 40.00, 500),
    }

    name, price, credits = packages[package]

    charge = client.charge.create({
        "name": name,
        "description": "YouTube StudyBuddy Credits",
        "pricing_type": "fixed_price",
        "local_price": {
            "amount": str(price),
            "currency": "USD"
        },
        "metadata": {
            "user_id": user_id,
            "credits": credits
        },
        "redirect_url": "https://your-app.com/success",
        "cancel_url": "https://your-app.com/cancel"
    })

    return charge.hosted_url  # User pays here with crypto wallet


# Webhook handler
@app.post("/webhook/coinbase")
async def coinbase_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("x-cc-webhook-signature")

    try:
        event = Webhook.construct_event(payload, sig_header,
                                       os.getenv("COINBASE_WEBHOOK_SECRET"))

        if event.type == "charge:confirmed":
            charge = event.data
            user_id = charge.metadata.user_id
            credits = charge.metadata.credits

            # Add credits to user
            user = clerk.users.get(user_id)
            current_credits = user.public_metadata.get("credits", 0)
            clerk.users.update(user_id, {
                "public_metadata": {
                    "credits": current_credits + credits
                }
            })

        return {"status": "success"}
    except Exception as e:
        return {"error": str(e)}, 400
```

---

### Conversion to ZAR

**Option 1: Keep stablecoins**
- Hold USDC in Coinbase Commerce
- Withdraw when needed
- No FX fees

**Option 2: Auto-convert**
- Use South African exchange APIs (Luno, VALR)
- Auto-sell USDC → ZAR on receipt
- Transfer to local bank account

**Option 3: Spend directly**
- Use crypto debit cards (Wirex, Crypto.com)
- Spend USDC/BTC directly
- AWS accepts crypto via BitPay

---

### Cost Comparison

| Solution | Fee | Settlement Time | FX Risk |
|----------|-----|-----------------|---------|
| Stripe (SA) | 2.9% + $0.30 + 3% FX | 7-14 days | High |
| Coinbase Commerce | 1% | Instant | None (USDC) |
| BTCPay Server | Network only (~$0.01) | Instant | Variable (BTC) |
| Strike | 0.3% | Instant | None (auto-convert) |
| Direct USDC | ~$0.01 | Instant | None |

---

### Recommendation for Your Use Case

**Best option: Coinbase Commerce with USDC**

**Why:**
1. ✅ 2-3 hour setup (as fast as Stripe)
2. ✅ 1% fee vs Stripe's 6%+ with FX
3. ✅ No currency conversion issues
4. ✅ Easy to cash out on SA exchanges
5. ✅ Users comfortable with either crypto or can buy USDC on Luno/VALR first
6. ✅ No volatility (USDC = $1 always)

**Implementation steps:**
1. Sign up for Coinbase Commerce
2. Replace Stripe code with Coinbase Commerce API
3. Add crypto payment option to Streamlit UI
4. Same webhook pattern as Stripe
5. Cash out to ZAR via Luno when needed

**Timeline:** 2-3 hours (same as Stripe integration)
**Total setup:** Clerk (2h) + Coinbase Commerce (2h) = **4 hours total**

---

### Hybrid Approach (Best UX)

Offer both payment methods:

```python
# In Streamlit UI
payment_method = st.radio("Payment method:",
                         ["Credit Card (Stripe)",
                          "Crypto (USDC/BTC)"])

if payment_method == "Credit Card (Stripe)":
    checkout_url = create_stripe_checkout(user.id, package)
else:
    checkout_url = create_crypto_checkout(user.id, package)

st.markdown(f"[Pay Now]({checkout_url})")
```

This way:
- International users use crypto (lower fees)
- Users without crypto can still use cards
- You maximize coverage and minimize fees
