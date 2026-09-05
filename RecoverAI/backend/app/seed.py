import random
from .database import Base, SessionLocal, engine
from .models import RecoveryCase

def seed(count=120, reset=False):
    Base.metadata.create_all(engine); db=SessionLocal()
    try:
        if reset: db.query(RecoveryCase).delete(); db.commit()
        if db.query(RecoveryCase).count(): return
        rng=random.Random(2026); reasons=["insufficient_balance","card_declined","expired_card","technical_error","authentication_failed"]
        for i in range(1,count+1):
            amount=round(rng.choice([499,799,1499,2499,4999,9999,14999,27999,49999])+rng.random()*100,2)
            db.add(RecoveryCase(merchant_id=f"merchant_{rng.randint(1,8):02}",payment_id=f"pay_test_{i:04}",customer_reference=f"cust_demo_{rng.randint(1,90):03}",failure_reason=rng.choice(reasons),amount=amount,previous_attempts=rng.randint(0,4),customer_history_score=round(rng.random(),2),customer_opted_out=rng.random()<.08,status="pending",idempotency_key=f"recoverai-seed-{i:04}"))
        db.commit()
    finally: db.close()
if __name__=="__main__": seed()

