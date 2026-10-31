"""Generate password hashes for the two CRM accounts; do not commit output."""
import getpass, hashlib, secrets
name=input("Account name: ").strip()
password=getpass.getpass("Password: ")
if len(password)<14: raise SystemExit("Use at least 14 characters.")
salt=secrets.token_bytes(16)
rounds=390000
value=hashlib.pbkdf2_hmac("sha256",password.encode(),salt,rounds)
print(f'{name} = "{rounds}${salt.hex()}${value.hex()}"')
