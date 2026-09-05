def test_health(client): assert client.get('/api/health').json()['status']=='ok'
def test_duplicate(client,auth):
    body={'merchant_id':'m','payment_id':'p','customer_reference':'c','failure_reason':'technical_error','amount':500,'previous_attempts':0,'customer_history_score':.7,'customer_opted_out':False,'idempotency_key':'same-key'}
    assert client.post('/api/cases',json=body,headers=auth).status_code==201
    assert client.post('/api/cases',json=body,headers=auth).status_code==409
def test_batch(client,auth,make_case):
    make_case();r=client.post('/api/cases/process-all',headers=auth);assert r.status_code==200 and r.json()['processed']==1

