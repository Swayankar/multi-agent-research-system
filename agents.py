from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_openrouter import ChatOpenRouter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from tools import web_search, scrape_url
from dotenv import load_dotenv
import os

load_dotenv()

# llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", temperature = 0)
# llm = ChatNVIDIA(model="nvidia/nemotron-3-ultra-550b-a55b")
llm = ChatOpenRouter(model="nvidia/nemotron-3-nano-30b-a3b:free", temperature=0)

# 1st Agent
def build_search_agent():
    return create_agent(
        model=llm,
        tools=[web_search]
    )

# 2nd Agent
def build_reader_agent():
    return create_agent(
        model=llm,
        tools=[scrape_url]
    )

# Writer chain
writer_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert research writer. Write clear, structured and insightful reports."),
    ("human", """Write a detailed research report on the topic below.

    Topic: {topic}
    Research Gathered:
    {research}

    Structure the report as:
    - Introduction
    - Key Findings (minimum 3 well-explained points)
    - Conclusion
    - Sources (list all URLs found in the research)

    Be detailed, factual and professional. And no need to include the created date in the report. Use the research gathered to support your points, and do not make up information.""")
])

writer_chain = writer_prompt | llm | StrOutputParser()

# Critic chain
critic_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a sharp and constructive research critic. Be honest and provide actionable feedback."),
    ("human", """Review the research report below and evaluate it strictly.

    Report:
    {report}

    Respond in this exact format:
    
    Score: X/10
    
    Strengths:
    - ...
    - ...
    
    Areas to improve:
    - ...
    - ...
    
    One line verdict:
    ...""")
])

critic_chain = critic_prompt | llm | StrOutputParser()
