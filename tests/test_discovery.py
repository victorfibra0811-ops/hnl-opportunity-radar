from radar.discovery import classify
def test_valid_b2b_still_unverified():
    x=classify("Fiber splicing subcontractors needed ASAP for current construction")
    assert x and x["stage"]=="UNVERIFIED" and not x["execution_ready"]
def test_no_individual_job():
    assert classify("Careers job openings for splicing technician subcontractors") is None
def test_no_future_auction():
    assert classify("Aerial subcontractors sought for auction and bid solicitation") is None
def test_new_services():
    for phrase in ("fiber blowing subcontractors needed","drop burial crews needed","restoration subcontractors needed"):
        assert classify(phrase)
