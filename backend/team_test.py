# https://docs.agno.com/basics/teams/building-teams
from agno.team import Team
from agno.agent import Agent
from agno.models.openai.like import OpenAILike
from agno.tools.duckduckgo import DuckDuckGoTools

# Configuration for local LLM
model = OpenAILike(
    id="deepseek-chat",
    api_key="sk-1234",
    base_url="http://localhost:4001/v1",
)

# Create specialized agents
news_agent = Agent(
    id="news-agent",
    name="News Agent",
    role="Get the latest news and provide summaries",
    model=model,
    tools=[DuckDuckGoTools()]
)

weather_agent = Agent(
    id="weather-agent",
    name="Weather Agent",
    role="Get weather information and forecasts",
    model=model,
    tools=[DuckDuckGoTools()]
)

# Create the team
team = Team(
    name="News and Weather Team",
    members=[news_agent, weather_agent],
    model=model,
    instructions="Coordinate with team members to provide comprehensive information. Delegate tasks based on the user's request."
)

team.print_response("What's the latest news and weather in Tokyo?", stream=True)