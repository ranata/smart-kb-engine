class State(TypedDict):
    query: str
    chatID: str
    route: str
    route_reason: str
    chat: str
    country: str
    default: str
    check: str
    health_code: str
    fetch_topic: str
    topic: str
    time_remain: float


class StateMachine:
    def __init__(self, state_context):
        self.tool_kit = tool_set.ToolKit(state_context)
        self.workflow = StateGraph(State)
        self.state_graph = None
        self.graph_shap = None

    def _check_route(self, state_message):
        next_tool = state_message["route"]
        allowed_route = ["RAG_processing", "response_default", "non_RAG"]
        if next_tool in allowed_route:
            return next_tool
        return "END"

    def build_graph(self):
        self.workflow.add_node("router", self.tool_kit.router)
        self.workflow.add_node("RAG_processing", self.tool_kit.RAG_processing)
        self.workflow.add_node("non_RAG", self.tool_kit.non_RAG_processing)
        self.workflow.add_node("response_default", self.tool_kit.response_default)
        self.workflow.add_node("guardrail_internal", self.tool_kit.guardrail_internal)

        self.workflow.add_edge(START, "router")

        route_mapping = {
            "RAG_processing": "RAG_processing",
            "response_default": "response_default",
            "non_RAG": "non_RAG",
            "END": END,
        }

        self.workflow.add_conditional_edges(
            "router", self._check_route, route_mapping
        )

        self.workflow.add_edge("RAG_processing", "guardrail_internal")
        self.workflow.add_edge("non_RAG", "guardrail_internal")
        self.workflow.add_edge("guardrail_internal", END)

        self.state_graph = self.workflow.compile()
        self.graph_shap = self.state_graph.get_graph().draw_ascii()

    def invoke(self, state):
        return self.state_graph.invoke(state)
