"""HNL shared cloud CRM. Cloud DB and individual credentials are required."""
import hashlib, hmac, os, json
from pathlib import Path
from datetime import date
import streamlit as st
import pandas as pd
import psycopg
from psycopg.rows import dict_row

st.set_page_config(page_title="HNL Opportunity Radar",layout="wide")
st.title("HNL Opportunity Radar")
st.caption("Kentucky | Fibra aérea e subterrânea")
st.markdown("""<style>.block-container{max-width:1450px;padding-top:2rem;padding-bottom:3rem}h1{font-weight:750;letter-spacing:-.04em}h2,h3{letter-spacing:-.025em}[data-testid="stMetric"]{background:rgba(107,139,156,.10);border:1px solid rgba(120,145,160,.22);border-radius:13px;padding:16px}[data-testid="stDataFrame"]{border:1px solid rgba(120,145,160,.25);border-radius:12px;overflow:hidden}[data-testid="stForm"]{border-radius:14px;border:1px solid rgba(120,145,160,.26)}div.stButton>button,div.stLinkButton>a{border-radius:9px}div.stButton>button[kind="primary"]{background:#dd7541;border-color:#dd7541}div[data-baseweb="select"]>div{border-radius:9px}section[data-testid="stSidebar"]{border-right:1px solid rgba(120,145,160,.25)}</style>""",unsafe_allow_html=True)
st.caption("Execution-ready B2B fiber projects • Shared CRM")

def config(name):
    try:
        return st.secrets.get(name)
    except (FileNotFoundError,KeyError):
        return None

def verify(password, value):
    try:
        rounds, salt, expected=value.split("$")
        actual=hashlib.pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(salt),int(rounds)).hex()
        return hmac.compare_digest(actual,expected)
    except (ValueError,AttributeError):
        return False

users=config("users") or {}
url=config("DATABASE_URL")
if not url or not users:
    st.error("Cloud CRM is not configured: DATABASE_URL and [users] must be set privately in Streamlit secrets.")
    st.stop()
if "user" not in st.session_state:
    with st.form("login"):
        username=st.text_input("Username")
        password=st.text_input("Password",type="password")
        submit=st.form_submit_button("Sign in")
    if submit:
        known=users.get(username,"")
        if verify(password,known):
            st.session_state["user"]=username
            st.rerun()
        else:
            st.error("Invalid credentials")
    st.stop()
with st.sidebar:
    st.write("Signed in:",st.session_state["user"])
    if st.button("Sign out"):
        del st.session_state["user"]
        st.rerun()
    page=st.radio("View",["Opportunities","CRM activity","Reports"])
def connect():
    return psycopg.connect(url, row_factory=dict_row, connect_timeout=15)
db_online=True
try:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id,project,company,state,city,service,stage,source_url,evidence,published_at,score,pipeline,updated_at FROM leads ORDER BY updated_at DESC LIMIT 2000")
            leads=cur.fetchall()
except psycopg.Error as exc:
    state=getattr(exc, "sqlstate", None)
    if state in ("28P01","28000"):
        reason="A senha ou o usuário do banco foi rejeitado pelo Neon."
    elif state=="3D000":
        reason="O nome do banco de dados não foi encontrado no servidor."
    elif state=="42P01":
        reason="A conexão abriu, mas a tabela leads não foi encontrada."
    elif isinstance(exc, psycopg.OperationalError):
        reason="Falha de autenticação, rede ou conexão. Confirme que DATABASE_URL foi copiada novamente do Neon após a última redefinição de senha."
    else:
        reason="Erro ao consultar o PostgreSQL. Verifique o esquema e a configuração do banco."
    # Show only a restricted error category. Never echo psycopg's raw exception
    # because some drivers append connection parameters to error messages.
    raw = str(exc).lower()
    if "password authentication failed" in raw:
        diagnostic = "AUTH_PASSWORD_REJECTED"
    elif "no pg_hba.conf entry" in raw:
        diagnostic = "PG_HBA_OR_SSL_POLICY"
    elif "name or service not known" in raw or "could not translate host name" in raw:
        diagnostic = "DNS_HOST_NOT_FOUND"
    elif "connection timed out" in raw or "timeout expired" in raw:
        diagnostic = "NETWORK_TIMEOUT"
    elif "connection refused" in raw:
        diagnostic = "NETWORK_REFUSED"
    elif "certificate verify failed" in raw or "ssl" in raw and "failed" in raw:
        diagnostic = "SSL_CONNECTION_ERROR"
    elif "role" in raw and "does not exist" in raw:
        diagnostic = "DATABASE_ROLE_MISSING"
    elif "database" in raw and "does not exist" in raw:
        diagnostic = "DATABASE_NAME_MISSING"
    elif "relation" in raw and "does not exist" in raw:
        diagnostic = "DATABASE_SCHEMA_MISSING"
    else:
        diagnostic = "OTHER_DATABASE_ERROR"
    st.error("Database connection failed.")
    st.info(reason)
    st.code(f"Diagnosis: {diagnostic} | SQLSTATE: {state or 'none'} | Exception: {type(exc).__name__}")
    db_online=False
    snapshot=Path(__file__).parent / "data" / "public_prospect_snapshot.json"
    try:
        leads=json.loads(snapshot.read_text(encoding="utf-8"))
        st.warning("MODO CONTINGÊNCIA: prospects públicos de 31/10/2026, não confirmados. CRM somente leitura até o Neon reconectar.")
    except (OSError, ValueError):
        st.error("Snapshot indisponível.")
        st.stop()

df=pd.DataFrame(leads)
if page=="Opportunities":
    st.metric("Prospects exibidos" if not db_online else "Stored leads",len(df))
    if not db_online:
        st.caption("Fonte: cópia pública de prospecção de 31/10/2026. Validação comercial pendente.")
    if df.empty:
        st.info("No leads in the shared cloud database yet. The scheduled collector must be configured and run.")
    else:
        state=st.selectbox("State",["All"]+sorted(x for x in df.state.dropna().unique()))
        category=st.selectbox("Service",["All"]+sorted(x for x in df.service.dropna().unique()))
        filtered=df.copy()
        if state!="All":filtered=filtered[filtered.state==state]
        if category!="All":filtered=filtered[filtered.service==category]
        status_names={"VENDOR_REGISTRATION":"Cadastro de fornecedor","AWARDED_OR_IDENTIFIED_UNVERIFIED":"Projeto identificado","UNVERIFIED_CREW_REQUEST":"Demanda a confirmar","UNVERIFIED":"Em investigação"}
        view=filtered.copy()
        view["Empresa"]=view["company"].fillna("Não identificada")
        view["Projeto / oportunidade"]=view["project"].fillna("")
        view["Tipo de fibra"]=view["service"].fillna("")
        view["Situação"]=view["stage"].map(lambda x:status_names.get(x,"Em investigação"))
        st.dataframe(view[["Empresa","Projeto / oportunidade","Tipo de fibra","Situação"]],hide_index=True,use_container_width=True)
        st.subheader("Contato comercial")
        selection=st.selectbox("Escolha uma oportunidade",filtered.index.tolist(),format_func=lambda i: str(filtered.loc[i,"company"] or filtered.loc[i,"project"]))
        chosen=filtered.loc[selection]
        contact_url=None
        if str(chosen.get("company") or "").lower().startswith("ervin"):
            contact_url="https://ervincable.com/subcontractors/"
        elif str(chosen.get("company") or "").lower().startswith("electricom"):
            contact_url="https://www.electricomllc.com/become-a-subcontractor"
        elif str(chosen.get("company") or "").lower().startswith("verita"):
            contact_url="https://veritacorp.com/subcontractors/"
        if contact_url:
            st.link_button("Abrir cadastro de fornecedor",contact_url)
        else:
            st.info("Contato direto não verificado. Consulte a fonte original para identificar o responsável.")
        if chosen.get("source_url"):
            st.link_button("Consultar fonte original",str(chosen["source_url"]))
        ident=st.selectbox("Update opportunity",filtered.id.tolist(),format_func=lambda i: next((str(x) for x in filtered.loc[filtered.id==i,"project"]),i)) if db_online and not filtered.empty else None
        if ident:
            stages=["NEW","QUALIFIED","CONTACTED","REPLIED","NEGOTIATING","PROPOSAL","WON","LOST"]
            with st.form("update"):
                pipeline=st.selectbox("CRM stage",stages)
                action=st.text_input("Action (e.g. phone call, email, follow-up)")
                detail=st.text_area("Notes")
                next_date=st.date_input("Next follow-up",value=date.today())
                if st.form_submit_button("Save activity"):
                    if not action.strip():
                        st.error("Describe the activity.")
                    else:
                        with connect() as conn:
                            with conn.cursor() as cur:
                                cur.execute("UPDATE leads SET pipeline=%s WHERE id=%s",(pipeline,ident))
                                cur.execute("INSERT INTO activities(lead_id,actor,action,detail,next_followup) VALUES(%s,%s,%s,%s,%s)",(ident,st.session_state["user"],action,detail,next_date))
                        st.success("Saved to shared CRM")
                        st.rerun()
elif page=="CRM activity" and not db_online:
    st.warning("CRM indisponível em modo contingência. Nenhuma alteração será salva.")
elif page=="CRM activity":
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT a.created_at,l.project,a.actor,a.action,a.detail,a.next_followup FROM activities a JOIN leads l ON l.id=a.lead_id ORDER BY a.created_at DESC LIMIT 500")
            items=cur.fetchall()
    st.dataframe(pd.DataFrame(items),use_container_width=True,hide_index=True)
else:
    st.info("Weekly report runs will be available when the GitHub Actions workflow is connected to Neon.")
