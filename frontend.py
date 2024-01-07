import os
import streamlit as st 
from dotenv import load_dotenv
from backend import load_db, load_embeddings, search

# Prep data
load_dotenv(".env")
KEY = os.getenv("HUGGINGFACEHUB_API_TOKEN")

model = load_embeddings(KEY)
db = load_db(model)

# Helper function
def pprint_name(name: str) -> str:
    """ Pretty print the name """
    return " ".join(
        map(
            lambda x: x[0].upper() + x[1:], 
            name.split("-")
        )
    )

# Context
st.title("Uwaterloo Prof Finder")
st.write("Search for some research topic on the side to find a relevant " + 
         "prof at the University of Waterloo.")

# Search inputs
with st.sidebar:
    with st.form(key='user_input'):
        query = st.text_input("Research Topic", max_chars=100,
                              placeholder="Data science in forestry")
        submit = st.form_submit_button("Search")

if submit and query:
    results = search(query, db)

    # Show summary results
    st.write("**Here are some profs you might want to reach out to**:")

    prof_str = "\n"
    prof_list = []
    for result in results:
        m = result.metadata
        name = pprint_name(m['name'])
        position = f"({m['position']})" if m['position'] else ""
        url = m['profile']
        if not url:
            url = f"https://www.google.com/search?q={'+'.join(name.split(' '))}+University+of+Waterloo"
        

        if name not in prof_list:
            prof_list.append(name)
            prof_str += f"- [{name}]({url}) {position}\n"

    st.write(prof_str + "\n\n")

    # Show detailed results
    st.write("\n**Here are some excerpts from their bios**:")
    
    prof_list = []
    for result in results:
        name = pprint_name(result.metadata['name'])
        if name not in prof_list:
            prof_list.append(name)
            st.write(f"{name}")
            st.write(result.page_content)
            st.write("\n")

# Error message
elif submit and not query:
    st.write("The query is empty. Please enter a research topic.")