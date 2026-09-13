"""
The multi-agent content pipeline, built as a LangGraph StateGraph.

Nodes (each is effectively its own "agent" with one job):
  1. research_node   -> ResearchAgent finds what's trending right now
  2. content_node    -> LLM writes meme text + an SEO-friendly caption/hashtags
  3. image_node       -> renders a meme image locally (Pillow)
  4. host_node        -> uploads the image somewhere public (imgbb)
  5. post_node        -> publishes to Instagram via the Graph API
  6. log_node         -> records the result in the local SQLite history

State flows through every node so each step can see what earlier steps did.
This structure is intentionally linear for the prototype, but LangGraph lets
you add conditional edges later (e.g. a human-approval node, or branching by
content_type) without restructuring anything.
"""
import json
from typing import TypedDict, List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END

from app.api.instagram_client import InstagramClient
from app.api.image_host import upload_image
from app.core.research import ResearchAgent
from app.core.image_generator import generate_meme_image
from app.core.llm_factory import get_llm
from app.core import db


class PipelineState(TypedDict, total=False):
    niche: str
    system_prompt: str
    content_type: str
    search_keywords: str
    hashtag_count: int
    access_token: str
    ig_user_id: str
    dry_run: bool

    trends: List[str]
    top_text: str
    bottom_text: str
    caption: str
    image_path: str
    image_url: str
    media_id: str
    error: Optional[str]


CONTENT_SCHEMA_PROMPT = ChatPromptTemplate.from_template(
    """You are the creative director of a viral Instagram page.

Niche: {niche}
Content type: {content_type}
Page voice / instructions: {system_prompt}

Here is what's trending right now, use it for inspiration (ignore anything irrelevant):
{trends}

Write content for ONE Instagram post. Respond with STRICT JSON only, no markdown
fences, no extra commentary, matching exactly this shape:

{{
  "top_text": "short punchy line for the top of the image (max 8 words)",
  "bottom_text": "short punchy line for the bottom of the image (max 8 words, can be empty string)",
  "caption": "the full Instagram caption: engaging, SEO-friendly, includes a hook,
              a short body, and ends with {hashtag_count} relevant hashtags"
}}
"""
)


def research_node(state: PipelineState) -> PipelineState:
    researcher = ResearchAgent()
    keywords = state.get("search_keywords") or state["niche"]
    trends = researcher.get_trending_topics(keywords)
    return {**state, "trends": trends}


def content_node(state: PipelineState) -> PipelineState:
    llm = get_llm()
    chain = CONTENT_SCHEMA_PROMPT | llm
    result = chain.invoke(
        {
            "niche": state["niche"],
            "content_type": state.get("content_type", "meme"),
            "system_prompt": state["system_prompt"],
            "trends": "\n".join(f"- {t}" for t in state.get("trends", [])) or "(no live trends found)",
            "hashtag_count": state.get("hashtag_count", 10),
        }
    )
    raw = result.content.strip()
    # Be defensive: strip accidental code fences if the model adds them anyway.
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.split("json", 1)[-1] if raw.lower().startswith("json") else raw
    parsed = json.loads(raw)
    return {
        **state,
        "top_text": parsed.get("top_text", ""),
        "bottom_text": parsed.get("bottom_text", ""),
        "caption": parsed.get("caption", ""),
    }


def image_node(state: PipelineState) -> PipelineState:
    path = generate_meme_image(state.get("top_text", ""), state.get("bottom_text", ""))
    return {**state, "image_path": path}


def host_node(state: PipelineState) -> PipelineState:
    url = upload_image(state["image_path"])
    return {**state, "image_url": url}


def post_node(state: PipelineState) -> PipelineState:
    if state.get("dry_run"):
        return {**state, "media_id": "DRY_RUN_NO_POST"}
    client = InstagramClient(state["access_token"], state["ig_user_id"])
    result = client.publish_image_post(state["image_url"], state["caption"])
    return {**state, "media_id": result.get("id", "")}


def log_node(state: PipelineState) -> PipelineState:
    db.add_post(
        media_id=state.get("media_id", ""),
        caption=state.get("caption", ""),
        trends=json.dumps(state.get("trends", [])),
        image_path=state.get("image_path", ""),
        status="dry_run" if state.get("dry_run") else "posted",
    )
    return state


def build_graph():
    graph = StateGraph(PipelineState)
    graph.add_node("research", research_node)
    graph.add_node("content", content_node)
    graph.add_node("image", image_node)
    graph.add_node("host", host_node)
    graph.add_node("post", post_node)
    graph.add_node("log", log_node)

    graph.set_entry_point("research")
    graph.add_edge("research", "content")
    graph.add_edge("content", "image")
    graph.add_edge("image", "host")
    graph.add_edge("host", "post")
    graph.add_edge("post", "log")
    graph.add_edge("log", END)

    return graph.compile()


def run_pipeline(config, dry_run: bool = False) -> PipelineState:
    """Entry point used by both the dashboard's 'Run Now' button and the scheduler."""
    app_graph = build_graph()
    initial_state: PipelineState = {
        "niche": config.niche,
        "system_prompt": config.system_prompt,
        "content_type": config.content_type,
        "search_keywords": config.search_keywords,
        "hashtag_count": config.hashtag_count,
        "access_token": config.access_token,
        "ig_user_id": config.ig_user_id,
        "dry_run": dry_run,
    }
    try:
        return app_graph.invoke(initial_state)
    except Exception as e:
        return {**initial_state, "error": str(e)}
