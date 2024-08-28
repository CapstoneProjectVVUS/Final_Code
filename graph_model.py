import os
from dotenv import load_dotenv
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain.utilities import DuckDuckGoSearchAPIWrapper
from langchain import hub, LLMMathChain
from langchain_community.tools.wikidata.tool import WikidataAPIWrapper, WikidataQueryRun
from langchain_community.utilities import GoogleSearchAPIWrapper
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers.openai_functions import JsonOutputFunctionsParser
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import CharacterTextSplitter
from langgraph.graph import END, StateGraph
from langchain.agents import AgentExecutor, create_openai_tools_agent
from typing import Optional, Type
from langchain.pydantic_v1 import BaseModel, Field
from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain_core.tools import BaseTool
from langchain_openai import OpenAIEmbeddings
import functools
import operator
from typing import Sequence, TypedDict, Annotated
import pandas as pd

load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ['LANGCHAIN_ENDPOINT']= os.getenv('LANGCHAIN_ENDPOINT')
os.environ['LANGCHAIN_API_KEY']= os.getenv('LANGCHAIN_API_KEY')
os.environ["GOOGLE_CSE_ID"] = os.getenv("GOOGLE_CSE_ID")
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
os.environ['LANGCHAIN_TRACING_V2']=os.getenv('LANGCHAIN_TRACING_V2')
os.environ["LANGCHAIN_PROJECT"] = "Final Agent"



##############################################################################



members = ["Archery", "Tennis", "Hockey", "Skateboarding", "Paris 2024 Schedule, Venues", "General/Other"]

def create_supervisor():
    '''Define the supervisor node for the graph workflow.'''   
    
    system_prompt = (
        "You are a supervisor tasked with managing a conversation between the"
        " following workers:  {members}. Given the following user request,"
        " respond with the worker to act next. Each worker will perform a"
        " task and respond with their results and status. When finished,"
        " respond with FINISH."
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

    return supervisor_chain


df = pd.read_csv("./Data/Schedule.csv")
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
llm = ChatOpenAI(model="gpt-3.5-turbo-0125", temperature=0.3)
# llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

wikipedia = WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())
# tavily_tool = TavilySearchResults(max_results=5)
llm_math_chain = LLMMathChain.from_llm(llm=llm, verbose=True)
search = DuckDuckGoSearchAPIWrapper()
wikidata = WikidataQueryRun(api_wrapper=WikidataAPIWrapper())
Google_search = GoogleSearchAPIWrapper()

from langchain_community.document_loaders import TextLoader

loader = TextLoader("./Data/List_of_Athletes.txt")
documents = loader.load()


text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
texts = text_splitter.split_documents(documents)
embeddings = OpenAIEmbeddings()
db = FAISS.from_documents(texts, embeddings)
retriever2 = db.as_retriever()

from langchain.tools import StructuredTool
from langchain.tools.retriever import create_retriever_tool
from hockey import obtain_live_score

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

    StructuredTool.from_function(
        name = "GoogleSearch",
        func = Google_search.run,
        description = "Useful to browse information from the internet to know recent results and information you don't know. Then, tell user the result."
    ),
]


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

hockey_tools = [structuredHockeyTool]



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

loader = TextLoader("./Data/SkateboardAthletes.txt")
documents = loader.load()

# loader2 = TextLoader("/content/SkateboaringSchedule.txt")
# documents2 = loader2.load()



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
    "skateboarding_athletes",
    "Searches for skateboarding athletes in Paris 2024 in 4 variations, Men(Park), Women(Park), Men(Street), Women(Street)",
)

# tool2 = create_retriever_tool(
#     retriever2,
#     "skateboarding_schedule_paris2024",
#     "Schedule for skateboarding events, Men(Park), Women(Park), Men(Street), Women(Street) in Paris 2024 ",
# )



tools3 = [tool1]



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
 You are not restricted to answering only from the document you will be provided. You can augment additonal knowledge if and when necessary to provide as much detail as possible.
 If the question is not related to skateboarding, ask the user to ask only related questions.
 Refer the user to https://www.worldskate.org/ which is the official skateboarding partner for the Paris 2024 Olympics, for any additional information."""

skateboarding_agent=create_agent(llm, tools3,system_prompt)

skateboarding_node = functools.partial(agent_node, agent=skateboarding_agent, name="Skateboarding")

base_prompt = """

       You are an AI chatbot assisting users with information regarding the Olympic for Paris 2024 schedule. Your primary data source is a pandas dataframe that contains detailed information about various Olympic events. Your goal is to answer questions related to the Olympic schedule accurately and concisely. You also have access to the venues where the event is being held so you can assist with queries regarding this as well. Here is an overview of the data structure you will be using:
Sport: The name of the Sport being held. If the user has a question about a particular sport(s), make sure you use this column for initial filtering, this is VERY IMPORTANT.
Event: Additional information about the sport event being held, contains specifications like Men or Women, the round of the event (preliminary, group stage, semifinal etc), and other sport specific information, make sure to use these to answer the question in further detail.
Venue Information: If queried about the location or venue details, include the venue name and the closest metro station for convenience.
Time Information: Clearly mention both the start and end times of the events in standard time format.
General Assistance: Provide any other relevant details such as the number of matches or any special notes included in the "Additional details" column.
Format Consistency: Ensure that all times are displayed in standard time format for user clarity.
**IMPORTANT**: All the string text in Columns apart from Data are in COMPLETE LOWERCASE. Make sure that while the query is being generated this is taken into consideration. This is VERY important.
Example Interactions:
User: What events are scheduled for July 24?
Chatbot: On July 24, the following events are scheduled:
Rugby Sevens, Pool Rounds - men's, from 15:30 to 22:00 at Stade de France (Closest Metro: Stade de France - Saint-Denis (RER D)).
Football, Group Stage (Men's), from 15:00 to 23:00 at multiple locations. Please check the official documentation for details.
User: Where is the women's handball preliminaries on July 25?
Chatbot: The women's handball preliminaries on July 25 are at Stade Pierre de Coubertin. The closest metro station is Porte de Vincennes (Metro 1).
User: What time does the handball preliminaries start on July 25?
Chatbot: The handball preliminaries on July 25 start at the following times:
09:00 to 12:30
14:00 to 17:30
19:00 to 22:30
Use the data accurately to ensure users receive reliable and helpful information regarding the Olympic events.
** NOTE ** : ALWAYS answer any question only after you have executed a query on the dataframe and recieved a satisfactory response. DO NOT hallucinate or provide response if you are not sure. Just inform the user you are not aware and request them to visit the official Olympic website for Paris 2024.
**NOTE** : The user may use terms like finals/gold medal match interchangeably. Make sure to search for both if you don't recieve an answer for the other. Also make a check for both final and finals if either doesn't return a satisfactory response.
**NOTE** : Athletics is in the sport column. If the user asks about events like Javelin, Discus, Running events (100m, 200m wtc) and other athletic-related events make sure to search for these in the event column AFTER filtering out the sport = "athletics".
"""


system_prompt=base_prompt+suffix

schedule_agent=create_agent(llm, tools4,system_prompt)

schedule_node = functools.partial(agent_node, agent=schedule_agent, name="Schedule")

hockey_agent = create_agent(llm, hockey_tools, "You are an expert in the sport of Hockey. Based on the user query, answer the question by checking the current hockey score. "
                            "The data provided to you has the gender of the player, the countries, the score and the match they may be playing."
                            "Based on the user query, answer the question by observing the context provided to you. Try to list out as much information as possible."
                            "If information pertaining to the question is not found, then specify that there is no information."
                            "Phrase everything POINTWISE. If you encounter a tie, then search the following page: https://www.fih.hockey/events/the-olympic-games-paris-2024/schedule-fixtures-results for further information on that match.")
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
supervisor_chain = create_supervisor()

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