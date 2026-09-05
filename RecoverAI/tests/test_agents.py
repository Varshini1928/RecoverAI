import pytest
from app.agents import calculate_score,choose_strategy,safety_decision
@pytest.mark.parametrize('reason,expected',[('technical_error','RETRY'),('insufficient_balance','RETRY'),('expired_card','REMIND'),('authentication_failed','REMIND'),('card_declined','ESCALATE')])
def test_strategies(reason,expected): assert choose_strategy(reason,0,.2 if reason=='card_declined' else .8)[0]==expected
def test_score(): assert calculate_score(25000,'technical_error',0,.9)>calculate_score(500,'expired_card',2,.2)
def test_max_retry(make_case): assert safety_decision(make_case(previous_attempts=3),'RETRY',.9)[2]=='MAX_THREE_RETRIES'
def test_expired_card(make_case): assert safety_decision(make_case(failure_reason='expired_card'),'RETRY',.9)[2]=='EXPIRED_CARD_NO_RETRY'
def test_low_confidence(make_case): assert safety_decision(make_case(),'RETRY',.69)[2]=='LOW_CONFIDENCE'
def test_high_value(make_case): assert safety_decision(make_case(amount=26000),'RETRY',.9)[2]=='HIGH_VALUE_APPROVAL_REQUIRED'
def test_optout(make_case): assert safety_decision(make_case(customer_opted_out=True),'REMIND',.9)[2]=='CUSTOMER_OPT_OUT'

