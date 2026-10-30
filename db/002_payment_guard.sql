-- Enforce payment limits centrally, including concurrent requests.
CREATE OR REPLACE FUNCTION hnl.validate_payment_balance()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE invoice_amount NUMERIC(18,2); current_paid NUMERIC(18,2);
BEGIN
  SELECT amount INTO invoice_amount FROM hnl.invoices WHERE id=NEW.invoice_id FOR UPDATE;
  IF invoice_amount IS NULL THEN RAISE EXCEPTION 'Invoice not found'; END IF;
  SELECT COALESCE(SUM(amount),0) INTO current_paid FROM hnl.payments
    WHERE invoice_id=NEW.invoice_id AND (TG_OP <> 'UPDATE' OR id<>NEW.id);
  IF current_paid + NEW.amount > invoice_amount THEN
    RAISE EXCEPTION 'Payment exceeds invoice balance';
  END IF;
  RETURN NEW;
END;
$$;
DROP TRIGGER IF EXISTS hnl_check_payment_balance ON hnl.payments;
CREATE TRIGGER hnl_check_payment_balance BEFORE INSERT OR UPDATE ON hnl.payments
FOR EACH ROW EXECUTE FUNCTION hnl.validate_payment_balance();
