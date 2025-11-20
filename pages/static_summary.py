
import streamlit as st
from pymongo import MongoClient


@st.cache_resource
def get_mongo_client():
    return MongoClient(st.secrets["MONGO_URI"])

db = get_mongo_client()["pls"]
users_collection = db["users"]

def static_summary(): 
     
    if "prolific_id" not in st.session_state:
        st.error("Please log in first.")
        return 
    
    st.title()
     


