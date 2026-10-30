-- Prevent lowering invoice below funds already received.
CREATE OR REPLACE FUNCTION hnl.prevent_invoice_underpayment()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE received NUMERIC(18,2);
BEGIN
 SELECT COALESCE(SUM(amount),0) INTO received FROM hnl.payments WHERE invoice_id=NEW.id;
 IF NEW.amount < received THEN
   RAISE EXCEPTION 'Invoice total cannot be less than recorded payments';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER hnl_guard_invoice_amount
BEFORE UPDATE OF amount ON hnl.invoices FOR EACH ROW
EXECUTE FUNCTION hnl.prevent_invoice_underpayment();
