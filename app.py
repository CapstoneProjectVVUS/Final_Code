
import streamlit as st
from graph_model import graph
from langchain_core.messages import BaseMessage, HumanMessage

####################################################################
def generate_response(question):
    response = graph.invoke(
        {
            "messages": [
                HumanMessage(content=question)
            ]
        }
    )
    print(response, type(response))
    return response["messages"][1].content


st.set_page_config(page_title="💬 Olympics Chatbot")

# Initialize session states if not already set
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Welcome to Paris 2024 Olympics Chatbot! How may I assist you?"}]
if 'chat_sessions' not in st.session_state:
    st.session_state.chat_sessions = {}
if 'selected_chat' not in st.session_state:
    st.session_state.selected_chat = None
    

st.sidebar.write("Existing Chat Sessions:")
if st.session_state.chat_sessions:
    for session_id in st.session_state.chat_sessions.keys():
        if st.sidebar.button(session_id):
            st.session_state.selected_chat = session_id
            st.session_state.messages = st.session_state.chat_sessions[session_id]
else:
    st.sidebar.write("No chat sessions available. Start a new one by entering a Chat Session ID below.")

new_chat_id = st.sidebar.text_input("Enter New Chat Session ID")
if st.sidebar.button("Start New Chat Session") and new_chat_id:
    if new_chat_id not in st.session_state.chat_sessions:
        st.session_state.chat_sessions[new_chat_id] = [{"role": "assistant", "content": "Welcome to Paris 2024 Olympics Chatbot! How may I assist you?"}]
    st.session_state.selected_chat = new_chat_id
    st.session_state.messages = st.session_state.chat_sessions[new_chat_id]


def clear_chat_history():
    st.session_state.messages = [{"role": "assistant", "content": "Welcome to Paris 2024 Olympics Chatbot! How may I assist you?"}]
st.sidebar.button('Clear Chat History', on_click=clear_chat_history)

if st.session_state.selected_chat:
    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
                # st.markdown(message["content"])
       
                
    if prompt := st.chat_input("Ask me anything"):
        # Add user message to chat history
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.spinner("Generating response..."):
            response = generate_response(prompt)
            print(response)
            with st.chat_message("assistant"):
                st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})