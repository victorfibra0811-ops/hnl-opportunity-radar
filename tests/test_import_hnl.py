from radar.import_hnl import as_lead
def test_not_confirmed():
    r=as_lead({"id":"HNL005","url_fonte":"https://example.com/notice","classificacao":"demanda_anunciada","estados":"KY"})
    assert r["stage"]=="UNVERIFIED_CREW_REQUEST"
    assert r["score"]==0
def test_individual_excluded():
    r=as_lead({"id":"HNL014","url_fonte":"https://example.com/jobs","classificacao":"contratado_individual","estados":"IL"})
    assert r["pipeline"]=="EXCLUDED"
