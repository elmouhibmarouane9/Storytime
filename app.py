import streamlit as st

st.set_page_config(page_title="My Awesome Website", page_icon="Rocket", layout="wide")

st.title("Welcome to My Free Python Website!")
st.markdown("Built with **Streamlit** and hosted 100% free!")

st.sidebar.header("About Me")
st.sidebar.write("Hi! I'm learning Python and this is my first website.")
st.sidebar.image("https://via.placeholder.com/200", caption="Your Photo")

col1, col2 = st.columns(2)

with col1:
    st.header("What I Do")
    st.write("""
    - Python Developer
    - Love building web apps
    - Learning AI & Machine Learning
    """)
    st.button("Say Hello")

with col2:
    st.header("My Projects")
    st.write("• Portfolio website (this one!)")
    st.write("• To-do list app")
    st.write("• Weather dashboard")
    st.image("https://via.placeholder.com/400x200")

st.header("Contact Me")
with st.form("contact_form"):
    name = st.text_input("Your Name")
    email = st.text_input("Your Email")
    message = st.text_area("Message")
    submitted = st.form_submit_button("Send")
    if submitted:
        st.success(f"Thanks {name}! I'll reply to {email} soon!")

st.markdown("---")
st.markdown("Made with Love using Streamlit • Hosted free on [Streamlit Cloud](https://streamlit.io)")
