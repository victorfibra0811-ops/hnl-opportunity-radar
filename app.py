"""HNL shared cloud CRM. Cloud DB and individual credentials are required."""
import hashlib, hmac, os
from datetime import date
import streamlit as st
import pandas as pd
import psycopg
from psycopg.rows import dict_row

st.set_page_config(page_title="HNL Opportunity Radar",layout="wide")
st.title("HNL Opportunity Radar")
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
    st.error("Database connection failed.")
    st.info(reason)
    st.stop()

df=pd.DataFrame(leads)
if page=="Opportunities":
    st.metric("Stored leads",len(df))
    if df.empty:
        st.info("No leads in the shared cloud database yet. The scheduled collector must be configured and run.")
    else:
        state=st.selectbox("State",["All"]+sorted(x for x in df.state.dropna().unique()))
        category=st.selectbox("Service",["All"]+sorted(x for x in df.service.dropna().unique()))
        filtered=df.copy()
        if state!="All":filtered=filtered[filtered.state==state]
        if category!="All":filtered=filtered[filtered.service==category]
        st.dataframe(filtered,hide_index=True,use_container_width=True)
        ident=st.selectbox("Update opportunity",filtered.id.tolist(),format_func=lambda i: next((str(x) for x in filtered.loc[filtered.id==i,"project"]),i)) if not filtered.empty else None
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
elif page=="CRM activity":
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT a.created_at,l.project,a.actor,a.action,a.detail,a.next_followup FROM activities a JOIN leads l ON l.id=a.lead_id ORDER BY a.created_at DESC LIMIT 500")
            items=cur.fetchall()
    st.dataframe(pd.DataFrame(items),use_container_width=True,hide_index=True)
else:
    st.info("Weekly report runs will be available when the GitHub Actions workflow is connected to Neon.")
