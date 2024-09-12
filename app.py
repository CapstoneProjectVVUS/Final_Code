
import streamlit as st
import os
from dotenv import load_dotenv
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain.utilities import DuckDuckGoSearchAPIWrapper
from langchain import hub, LLMMathChain
from langchain.agents import Tool, AgentType, initialize_agent
from langchain.agents import AgentExecutor
from langchain_community.tools.wikidata.tool import WikidataAPIWrapper, WikidataQueryRun
from langchain.tools.render import render_text_description
from langchain_community.utilities import GoogleSearchAPIWrapper


load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ['LANGCHAIN_ENDPOINT']= os.getenv('LANGCHAIN_ENDPOINT')
os.environ['LANGCHAIN_API_KEY']= os.getenv('LANGCHAIN_API_KEY')
os.environ["GOOGLE_CSE_ID"] = os.getenv("GOOGLE_CSE_ID")
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
os.environ['LANGCHAIN_TRACING_V2']=os.getenv('LANGCHAIN_TRACING_V2')
os.environ["LANGCHAIN_PROJECT"] = "Final Agent"

st.set_page_config(page_title="💬 Olympics Chatbot")


##############################################################################


# def setup():
import pandas as pd
from langchain_openai import OpenAI

df = pd.read_csv("./Data/My Paris Olympics 2024 - All events_Updated.csv")
pd.set_option('display.max_columns', None)
# df[df['Event'].str.contains('finals') & df['Sport'].str.contains('Table tennis')]

columns_to_lowercase = ['Sport', 'Event', 'Additional details', 'Location', 'Closest Metro']

# Apply the str.lower function to the specified columns
df[columns_to_lowercase] = df[columns_to_lowercase].applymap(lambda x: x.lower() if isinstance(x, str) else x)


from langchain_experimental.agents.agent_toolkits.pandas.prompt import FUNCTIONS_WITH_DF
df_head = str(df.head(5).to_markdown())
suffix = (FUNCTIONS_WITH_DF).format(df_head=df_head)
# print(suffix)

from langchain_experimental.tools.python.tool import PythonAstREPLTool
tools4 = [PythonAstREPLTool(locals={"df": df})]

from langchain_openai import ChatOpenAI
# llm = ChatOpenAI(model="gpt-3.5-turbo-0125", temperature=0.3)
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

wikipedia = WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())
# tavily_tool = TavilySearchResults(max_results=5)
llm_math_chain = LLMMathChain.from_llm(llm=llm, verbose=True)
search = DuckDuckGoSearchAPIWrapper()
wikidata = WikidataQueryRun(api_wrapper=WikidataAPIWrapper())
Google_search = GoogleSearchAPIWrapper()

from langchain_community.document_loaders import TextLoader

loader = TextLoader("./Data/List_of_Athletes.txt")
documents = loader.load()

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import CharacterTextSplitter

text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
texts = text_splitter.split_documents(documents)
embeddings = OpenAIEmbeddings()
db = FAISS.from_documents(texts, embeddings)
retriever2 = db.as_retriever()


loader = TextLoader("./Data/RecurveParis2024Results.txt")
documents = loader.load()

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import CharacterTextSplitter

text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
texts = text_splitter.split_documents(documents)
embeddings = OpenAIEmbeddings()
db_recurve = FAISS.from_documents(texts, embeddings)
retriever_recurve = db_recurve.as_retriever()

from langchain.agents import Tool, load_tools
from langchain.tools import StructuredTool
from langchain.tools.retriever import create_retriever_tool

import bs4
import requests
from langchain_community.document_loaders import UnstructuredHTMLLoader
from datetime import date
from hockey import obtain_live_score
# def obtain_live_score():

#     response = open("./Data/prev.html", "r", encoding='utf-8').read()

#     soup = bs4.BeautifulSoup(response, 'html.parser')
#     output_list = []
#     # Iterate over all 'fixtures-listing-bottom' divs
#     for listing in soup.find_all('div', class_='fixtures-listing-bottom'):
#         # Extract the fixture title
#         title_div = listing.find('div', class_='fixtures-head')
#         if title_div:
#             title = title_div.find('h4', class_='fixtures-title').get_text(strip=True)
#         # Iterate over each fixture group
#         for fixture in listing.find_all(class_='fixtures-body'):
#             for fixtures_group in fixture.find_all(class_='fixtures-group'):

#                 top_container = fixture.find(class_="fixtures-top")
#                 # Find the mens fixture container or womens container
#                 gender_container = top_container.find(class_="fixtures-gender--mens")
#                 if gender_container == None:
#                     womens_container = top_container.find(class_="fixtures-gender--womens")
#                 #Extract the gender of the current matchup
#                 gender = gender_container.get_text().strip()
#                 # print(gender)
#                 # exit(0)
#                 for match in fixtures_group.find_all('li', class_='live hand-cursor'):
#                     # print(match)
#             # Extract team names
#                     teams = match.find_all('p', class_='team-name')
#                     teams_list = []
#                     for team in teams:
#                         team.get_text(strip=True)
#                         teams_list.append(team.get_text().strip())

#                     # print(teams_list)
#                     team_a, team_b = teams_list[0], teams_list[1]
#                     # exit(0)
#                     # team_b = match.find('div', class_='team team-b').find('p', class_='team-name').get_text(strip=True)
#                     # Extract scores
#                     scores = match.find_all('p', class_='score')
#                     scores_list = []
#                     for score in scores:
#                         scores_list.append(score.get_text().strip())
#                     # print(scores_list)
#                     score_a, score_b = scores_list[0], scores_list[1]

#                     # Extract match time
#                     match_time = match.find('div', class_='team-time').find('div', class_='timer-counter').get_text(strip=True)
#                     match_time = match_time[:-1] + " minutes"
#                     # print(match_time)

#                     # Extract venue
#                     # venue_div = match.find('div', class_='fixtures-venue')
#                     # if venue_div:
#                     #     venue = venue_div.find('p', class_='venue').get_text(strip=True)
#                     # else:
#                     #     venue = 'Unknown Venue'
#                     # print(venue)
#                     # Generate the sentence of information
#                     sentence = f"{title}: {team_a} (score: {score_a}) vs {team_b} (score: {score_b}) at {match_time}."
#                     output_list.append(sentence)
#                 # Print the sentence
#                     # print(sentence)
#     return sentence


# from hockey_tool import get_live_scores
def get_live_scores_tool() -> list:
    '''Obtains the live scores of hockey games in Paris 2024 Olympics.'''
    return obtain_live_score()


tools2 = [

    create_retriever_tool(
        retriever2,
        "List_of_Athletes",
        "Use only when you want list of all Paris 2024 Olympics archery athletes from different countries.",
    ),

    create_retriever_tool(
        retriever_recurve,
        "Recurve_Final_Standings_Paris_2024",
        "Use when user asks about the recurve archery standings for Paris 2024.",
    ),

    StructuredTool.from_function(
        name = "GoogleSearch",
        func = Google_search.run,
        description = "Useful to browse information from the internet to know recent results and information you don't know. Then, tell user the result."
    ),



]

from langchain.agents import Tool, load_tools

tools = [
    StructuredTool.from_function(
        name = "Search",
        func = search.run,
        description = "Useful to browse information from the internet to know recent results and information you don't know. Then, tell user the result."
    ),

    StructuredTool.from_function(
        name = "Wikipedia",
        func = wikipedia.run,
        description = "Use to get additional information about the named entities in the query asked by the user"
    ),
]

from typing import Optional, Type
from langchain.pydantic_v1 import BaseModel, Field
from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain_core.tools import BaseTool


class HockeyAgentInput(BaseModel):
    query: str = Field(description="query")


class CustomHockeyTool(BaseTool):
    name = "Hockey"
    description = "useful for finding the live score of hockey. Paraphrase based on the query."
    args_schema: Type[BaseModel] = HockeyAgentInput
    return_direct: bool = True

    def _run(
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> list:
        """Use the tool."""
        return obtain_live_score()

    async def _arun(
        self, run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        """Use the tool asynchronously."""
        # If the calculation is cheap, you can just delegate to the sync implementation
        # as shown below.
        # If the sync calculation is expensive, you should delete the entire _arun method.
        # LangChain will automatically provide a better implementation that will
        # kick off the task in a thread to make sure it doesn't block other async code.
        return self._run(run_manager=run_manager.get_sync())

structuredHockeyTool = StructuredTool.from_function(
    func=CustomHockeyTool._run,
    name="Hockey",
    description="useful for finding the live score of hockey. Paraphrase based on the query",
)

hockey_tools = [
                    structuredHockeyTool,
                    StructuredTool.from_function(
                        name = "Wikipedia",
                        func = wikipedia.run,
                        description = "Use to get deeper information about the matches played. If a tie is encountered, search for the result. If details about a match is asked, use this tool."
                    )
      ]



from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# prompt = ChatPromptTemplate.from_messages(
#     [
#         (
#             "system",
#             """
#             You are a question-answering assistant and your job is to answer any questions related to the Archery event in the Olympics.
#             Provide concise and precise 5 sentence answers.
#             Utlize the tools provided to you in inorder to produce the most accurate and upto date answer.
#             """
#         ),
#         # ("user", "{input}"),
#         MessagesPlaceholder(variable_name="messages"),
#         MessagesPlaceholder(variable_name="agent_scratchpad"),
#     ]
# )

# llm_with_tools = llm.bind_tools(tools)

from langchain.agents.format_scratchpad.openai_tools import (
    format_to_openai_tool_messages,
)
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser

# archery_agent = (
#     {
#         # "input": lambda x: x["input"],
#         "agent_scratchpad": lambda x: format_to_openai_tool_messages(
#             x["intermediate_steps"]
#         ),
#     }
#     | prompt
#     | llm_with_tools
#     | OpenAIToolsAgentOutputParser()
# )

from langchain.agents import AgentExecutor

# archery_agent_executor = AgentExecutor(agent=archery_agent, tools=tools, verbose=False)


def create_agent(llm: ChatOpenAI, tools: list, system_prompt: str):
    # Each worker node will be given a name and some tools.
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                system_prompt,
            ),
            MessagesPlaceholder(variable_name="messages"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )
    agent = create_openai_tools_agent(llm, tools, prompt)
    print(agent)
    executor = AgentExecutor(agent=agent, tools=tools)
    return executor


def agent_node(state, agent, name):
    result = agent.invoke(state)
    return {"messages": [HumanMessage(content=result["output"], name=name)]}


from langchain_core.output_parsers.openai_functions import JsonOutputFunctionsParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import Annotated

members = ["Archery", "Tennis", "Hockey", "Skateboarding", "Paris 2024 Schedule, Venues", "General/Other"]
system_prompt = (
    "You are a supervisor tasked with managing a conversation between the"
    " following workers:  {members}. Given the following user request,"
    " respond with the worker to act next. Each worker will perform a"
    " task and respond with their results and status. When finished,"
    " respond with FINISH. You HAVE to choose ONLY from these members."
)
# Our team supervisor is an LLM node. It just picks the next agent to process
# and decides when the work is completed
options = ["FINISH"] + members
# Using openai function calling can make output parsing easier for us
function_def = {
    "name": "route",
    "description": "Select the next role.",
    "parameters": {
        "title": "routeSchema",
        "type": "object",
        "properties": {
            "next": {
                "title": "Next",
                "anyOf": [
                    {"enum": options},
                ],
            }
        },
        "required": ["next"],
    },
}
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="messages"),
        (
            "system",
            "Given the conversation above, who should act next?"
            " Or should we FINISH? Select one of: {options}",
        ),
    ]
).partial(options=str(options), members=", ".join(members))

# llm = ChatOpenAI(model="gpt-3.5-turbo-0125")

supervisor_chain = (
    prompt
    | llm.bind_functions(functions=[function_def], function_call="route")
    | JsonOutputFunctionsParser()
)


# !pip install langchain_openai
# !pip install langchain
# !pip install langchain-community
# !pip install faiss-gpu
# prompt = ChatPromptTemplate.from_messages(
#     [
#         (
#             "system",
#             "You are an expert in the sport of Skateboarding. Answer these questions in as much detail as possible and provide all the information you know. You are not restricted to answering only from the document you will be provided. You can augment additonal knowledge if and when necessary to provide as much detail as possible. If the question is not related to skateboarding, ask the user to ask only related questions. Refer the user to https://www.worldskate.org/ which is the official skateboarding partner for the Paris 2024 Olympics, for any additional information.",
#         ),
#         ("user", "{input}"),
#         MessagesPlaceholder(variable_name="agent_scratchpad"),
#     ]
# )

from langchain_community.document_loaders import TextLoader

loader = TextLoader("./Data/SkateboardAthletes.txt")
documents = loader.load()

# loader2 = TextLoader("/content/SkateboaringSchedule.txt")
# documents2 = loader2.load()

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import CharacterTextSplitter

text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
texts = text_splitter.split_documents(documents)
embeddings = OpenAIEmbeddings()
db = FAISS.from_documents(texts, embeddings)

# text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
# texts2 = text_splitter.split_documents(documents2)
# db2 = FAISS.from_documents(texts2, embeddings)

retriever = db.as_retriever()
# retriever2 = db2.as_retriever()


from langchain.tools.retriever import create_retriever_tool

tool1 = create_retriever_tool(
    retriever,
    "skateboarding_athletes_qualifiers",
    "Searches for skateboarding athletes in the Paris 2024 qualifier series in 4 variations, Men(Park), Women(Park), Men(Street), Women(Street)",
)

# tool2 = create_retriever_tool(
#     retriever2,
#     "skateboarding_schedule_paris2024",
#     "Schedule for skateboarding events, Men(Park), Women(Park), Men(Street), Women(Street) in Paris 2024 ",
# )



tools3 = [tool1,
          
        StructuredTool.from_function(
        name = "Wikipedia",
        func = wikipedia.run,
        description = "Use this wikipedia tool to answer any questions that cannot be answered with your existing knowledge or the retriever. Also use this tool to provide any additional information that may be useful."
    )
          
          
          ]
from langchain.agents import AgentExecutor, create_openai_tools_agent



import functools
import operator
from typing import Sequence, TypedDict

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from langgraph.graph import END, StateGraph


# The agent state is the input to each node in the graph
class AgentState(TypedDict):
    # The annotation tells the graph that new messages will always
    # be added to the current states
    messages: Annotated[Sequence[BaseMessage], operator.add]

    # The 'next' field indicates where to route to next
    next: str


# research_agent = create_agent(llm, [tavily_tool], "You are a web researcher.")
# research_node = functools.partial(agent_node, agent=research_agent, name="Researcher")


# system_prompt='''You are very powerful information retrival system that can retrive information about entities in the user's query using the tools provided to you.
#             You only retrive information about entities related to the sport Archery played in the Olympics.


#             It is extremely important that every single time, you must get the output for the user query from ALL THE RELEVANT tools AVAILABLE and combine all the outputs to get a single output.
#             '''.
#  In case multiple questions are asked, obtain the anwer for each question ONE AT A TIME and combine all the answers to produce one result.

#sike prompt
# system_prompt='''You are an expert in the sport of Archery. Answer these questions in as much detail as possible and provide all the information you know.
#  Use Multiple Tool calls when required.
#  Use the GoogleSearch tool to get recent and additional information that is needed to answer the users query.
#  Use the List_of_Athletes retriever tool ONLY when you want list of all PARIS 2024 OLYMPICS archery athletes from different countries.
#  In case multiple questions are asked, use MULTIPLE tool calls to answer one question in one tool call and combine the result of all the answers.

#             '''

system_prompt='''
You are an expert in the sport of Archery. Answer these questions in as much detail as possible and provide all the information you know.
 Don't ask the user if they want additional information, Use your search tool and find additional information and show that output to the user.
 You are not restricted to using only one tool to answer a question. USE BOTH TOOLS IF REQUIRED.
 Use the GoogleSearch tool to get recent and additional information that is needed to answer the users query.
 Use the List_of_Athletes retriever tool ONLY when you want list of all PARIS 2024 OLYMPICS archery athletes from different countries.
 In case multiple questions are asked, use MULTIPLE tool calls to answer one question in one tool call and combine the result of all the answers.


'''

# system_prompt="""You are an expert in the sport of Archery. Answer these questions in as much detail as possible and provide all the information you know.
#  You are not restricted to answering only from the document you will be provided. You can augment additonal knowledge if and when necessary to provide as much detail as possible.
#  If the question is not related to archery, ask the user to ask only related questions.
#  Refer the user to https://www.worldarchery.sport/ which is the official archery partner for the Paris 2024 Olympics, for any additional information."""
archery_agent=create_agent(llm,tools2,system_prompt)
archery_node = functools.partial(agent_node, agent=archery_agent, name="Archery")

# NOTE: THIS PERFORMS ARBITRARY CODE EXECUTION. PROCEED WITH CAUTION
# code_agent = create_agent(
#     llm,
#     [python_repl_tool],
#     "You may generate safe python code to analyze data and generate charts using matplotlib.",
# )
system_prompt='''You are very powerful information retrival system that can retrive information about entities in the user's query using the tools provided to you.
            You only retrive information about entities related to the sport Tennis played in the Olympics.

            You have two tools are your disposal: the Wikipedia tool and the Search tool.
            Every single time, you must use both the tools available to you to get detailed information about the different entities present in the users query.
            '''
tennis_agent=create_agent(llm,tools,system_prompt)
tennis_node = functools.partial(agent_node, agent=tennis_agent, name="Tennis")

system_prompt="""You are an expert in the sport of Skateboarding. Answer these questions in as much detail as possible and provide all the information you know.
 You are not restricted to answering only from the document you will be provided. You can augment additonal knowledge if and when necessary to provide as much detail as possible. Make sure that the information you provide is 
 completely accurate and provide this in as much detail as possible. If you have any additional information about any athletes that you find from the retriever tool, make sure to provide this. The athletes you retrieve from the tool are competing
 in the QUALIFIER for the Olympics and not in the actualy olympics YET.
 Refer the user to https://www.worldskate.org/ which is the official skateboarding partner for the Paris 2024 Olympics, for any additional information."""

skateboarding_agent=create_agent(llm, tools3,system_prompt)

skateboarding_node = functools.partial(agent_node, agent=skateboarding_agent, name="Skateboarding")

base_prompt = """
  You are an AI chatbot assisting users with information regarding the Olympic for Paris 2024 schedule. Your primary data source is a pandas dataframe that contains detailed information about various Olympic events. Your goal is to answer questions related to the Olympic schedule accurately and concisely. Here is an overview of the data structure you will be using:
Sport:  **VERY IMPORTANT**. The name of the Sport being held. If the user has a question about a particular sport(s), make sure you use this column for initial filtering. Use the SPORT column to filter out for sport inititially, THEN use the event column.
Event: Additional information about the sport event being held, contains specifications like Men or Women, the round of the event (preliminary, group stage, semifinal etc), and other sport specific information, make sure to use these to answer the question in further detail.
Venue Information: If queried about the location or venue details, include the venue name and the closest metro station for convenience.
Time Information: Clearly mention both the start and end times of the events in standard time format.
General Assistance: Provide any other relevant details such as the number of matches or any special notes included in the "Additional details" column.
Format Consistency: Ensure that all times are displayed in standard time format for user clarity.
**IMPORTANT**: All the string text in Columns apart from Data are in COMPLETE LOWERCASE. Make sure that while the query is being generated this is taken into consideration. This is VERY important.
Example Interactions:
User: What events are scheduled for July 24?
Chatbot: On July 24, the following events are scheduled:
Rugby Sevens, Pool Rounds - men's, from 15:30 at Stade de France (Closest Metro: Stade de France - Saint-Denis (RER D)).
Football, Group Stage (Men’s), from 15:00  at multiple locations. Please check the official documentation for details.
User: Where is the women’s handball preliminaries on July 25?
Chatbot: The women’s handball preliminaries on July 25 are at Stade Pierre de Coubertin. The closest metro station is Porte de Vincennes (Metro 1).
User: What time does the handball preliminaries start on July 25?
Chatbot: The handball preliminaries on July 25 start at the following times:
09:00 (Paris Time)
14:00 (Paris Time)
19:00 (Paris Time)
Use the data accurately to ensure users receive reliable and helpful information regarding the Olympic events.
**IMPORTANT**: Make sure that ALL the columns you need are available to provide the response after you obtain the results of the execution of the Python query.
** NOTE ** : ALWAYS anwer any question only after you have executed a query on the dataframe and recieved a satisfactory response. DO NOT hallucinate or provide response if you are not sure. Just inform the user you are not aware and request them to visit the official Olympic website for Paris 2024.
**NOTE** : The user may use terms like finals/gold medal match interchangeably. Make sure to search for both if you don't recieve an answer for the other. ALso make a check for both final and finals if either doesn't return a satisfactory response.
**NOTE** : For events like Judo,Boxing and Wrestling, information about the weight classes and nature of rounds (eliminatory or medal) can be present in the additional details column so MAKE SURE to check for this column as well for these sports. ALWAYS make a check this column for the sports I mentioned.
**EXCEPTIONS ** : For football related queries, the medal matches have BRONZE AND GOLD in them instead of FINAL. So, use GOLD or BRONZE for searching instead of final.
"""


system_prompt=base_prompt+suffix

schedule_agent=create_agent(llm, tools4,system_prompt)

schedule_node = functools.partial(agent_node, agent=schedule_agent, name="Schedule")

hockey_agent = create_agent(llm, hockey_tools, "You are an expert in the sport of Hockey. Based on the user query, answer the question by checking the current hockey score."
                            "The data provided to you has the gender of the player, the countries, the score and the match they may be playing."
                            "Based on the user query, answer the question by observing the content provided to you. List out as much information as possible!. DO NOT NEGLECT THE GENDER."
                            "If zero information pertaining to the question is not found, then tell 'there is no information available on this'."
                            "Phrase everything POINTWISE. If you encounter a tie, then use the Wikipedia tool.")
hockey_node = functools.partial(agent_node, agent=hockey_agent, name="Hockey")


# 33333333333333333333333333333333333333333333333333333333333333333333333333333333333333

system_prompt="""I am an expert on Olympic related queries, specfically Paris 2024. I answer user queries with a high level of detail and accuracy and tell the user i dont know the
answer if i am not aware of it and refer them to the official Olympic website www.olympics.org. I enjoy having conversations with people but don't answer queries that are far beyond the Olympics
 as i am not specialized in them. You will also have access to a search tool."""

tools_empty = [
    StructuredTool.from_function(
        name = "Duck_Search",
        func = search.run,
        description = "Useful to browse information from the internet to know recent results and information you don't know. Then, tell user the result."
    ),

]

other_agent=create_agent(llm, tools_empty, system_prompt)

other_node = functools.partial(agent_node, agent=other_agent, name="Other")


# print("##################################")
# print(archery_node)
# print("##################################")

# print(skateboarding_node)

workflow = StateGraph(AgentState)
print("##################################")
print(workflow)
print("##################################")
workflow.add_node("Tennis", tennis_node)
workflow.add_node("Archery", archery_node)
workflow.add_node("Skateboarding", skateboarding_node)
workflow.add_node("Paris 2024 Schedule, Venues", schedule_node)
workflow.add_node("Hockey", hockey_node)
workflow.add_node("General/Other", other_node)
workflow.add_node("supervisor", supervisor_chain)


# for member in members:
#     # We want our workers to ALWAYS "report back" to the supervisor when done
#     workflow.add_edge(member, "supervisor")
# The supervisor populates the "next" field in the graph state
# which routes to a node or finishes
conditional_map = {k: k for k in members}
# conditional_map["FINISH"] = END
workflow.add_conditional_edges("supervisor", lambda x: x["next"], conditional_map)
# Finally, add entrypoint
workflow.set_entry_point("supervisor")

graph = workflow.compile()



####################################################################


# Initialize session states if not already set

import streamlit as st
from langchain.schema import HumanMessage, AIMessage
import re

# Custom CSS for Olympic theme
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');

    .stApp {
        background-color: #f0f0f0;
        font-family: 'Roboto', sans-serif;
    }
    .main .block-container {
        padding-top: 2rem;
    }
    h1, h2, h3 {
        color: #0081C8;
    }
    .css-1d391kg {
        background-color: #f0f0f0;
    }
    .stButton>button {
        background-color: #0081C8;
        color: white;
        border-radius: 20px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #005c8f;
    }
    .stTextInput>div>div>input {
        border-color: #0081C8;
        border-radius: 20px;
    }
    .stChatMessage {
        background-color: #ffffff;
        border-radius: 15px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .stChatMessage.user {
        background-color: #e6f3ff;
    }
    .stChatMessage .content p {
        margin-bottom: 0;
    }
</style>
""", unsafe_allow_html=True)

st.title("Paris 2024 Olympics Chatbot")

if "messages" not in st.session_state:
    st.session_state.messages = []
if 'chat_sessions' not in st.session_state:
    st.session_state.chat_sessions = {}
if 'selected_chat' not in st.session_state:
    st.session_state.selected_chat = None
if 'new_session' not in st.session_state:
    st.session_state.new_session = True

def generate_session_name(message):
    words = re.findall(r'\b\w+\b', message.lower())
    stopwords = set(['the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'])
    key_words = [word for word in words if word not in stopwords]
    session_name = ' '.join(key_words[:min(5, len(key_words))])
    return session_name.capitalize()

st.sidebar.title("Chat Sessions")
if st.session_state.chat_sessions:
    st.sidebar.markdown("Existing Chat Sessions:")
    for session_id in st.session_state.chat_sessions.keys():
        if st.sidebar.button(f"📅 {session_id}"):
            st.session_state.selected_chat = session_id
            st.session_state.messages = st.session_state.chat_sessions[session_id]
            st.session_state.new_session = False
else:
    st.sidebar.info("No chat sessions available. Start chatting to create a new session!")

def clear_chat_history():
    if st.session_state.selected_chat:
        del st.session_state.chat_sessions[st.session_state.selected_chat]
    st.session_state.messages = []
    st.session_state.new_session = True
    st.session_state.selected_chat = None

st.sidebar.button('🗑️ Clear Chat History', on_click=clear_chat_history)

def generate_response(question, chat_history):
    messages = [
        AIMessage(content=msg["content"]) if msg["role"] == "assistant" else HumanMessage(content=msg["content"])
        for msg in chat_history
    ]
    messages.append(HumanMessage(content=question))
    
    response = graph.invoke({"messages": messages})
    return response["messages"][-1].content

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask about the Paris 2024 Olympics..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    if st.session_state.new_session:
        session_name = generate_session_name(prompt)
        st.session_state.selected_chat = session_name
        st.session_state.new_session = False
    
    with st.spinner("🏅 Generating response..."):
        response = generate_response(prompt, st.session_state.messages)
        with st.chat_message("assistant"):
            st.markdown(response)
    
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.session_state.chat_sessions[st.session_state.selected_chat] = st.session_state.messages

if st.session_state.selected_chat:
    st.sidebar.success(f"Current Session: {st.session_state.selected_chat}")

# Footer
st.markdown("---")
st.markdown("🏅 Powered by AI - Bringing the Olympic spirit to your conversations!")


