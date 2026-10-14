package devbuddy.agent;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * A hand-rolled state machine — the graph runtime (Java's note in pom.xml:
 * "Week 6 (Agent): No extra dep — hand-rolled state machine").
 *
 * <p>Nodes are functions. Edges are data ({@link Route} functions that read
 * state and name the next node). The RUNTIME walks them — no demo writes a
 * node-to-node for-loop, exactly like LangGraph's compile() in Python/Node:</p>
 *
 * <pre>
 *   current = start
 *   loop:  state = nodes[current].run(state)      ← node records itself
 *          current = routes[current].next(state)   ← pure read of state
 *   until  current == END
 * </pre>
 */
public final class Graph {

    /** Terminal marker — never a node name. */
    public static final String END = "__end__";

    /** One node: takes state, mutates + records, returns it. */
    public interface Node {
        AgentState run(AgentState state);
    }

    /** A router: reads state (pure), returns the next node name or END. */
    public interface Route {
        String next(AgentState state);
    }

    /** Transition listener — how demo-01 "streams" the graph. */
    public interface Listener {
        void onNode(String node, AgentState state);
    }

    private final String start;
    private final Map<String, Node> nodes;
    private final Map<String, Route> routes;

    private Graph(Builder b) {
        this.start = b.start;
        this.nodes = b.nodes;
        this.routes = b.routes;
    }

    public static Builder from(String start) {
        return new Builder(start);
    }

    /** Compile-time surface: which node ids are wired in (tests assert on it). */
    public java.util.Set<String> nodeNames() {
        return java.util.Collections.unmodifiableSet(nodes.keySet());
    }

    /** Run until END. The runtime drives the transitions — this loop belongs
     *  to the graph, never to a demo or a node. */
    public AgentState run(AgentState state) {
        return run(state, null);
    }

    /** Same, reporting every transition — how demo-01 "streams" the graph. */
    public AgentState run(AgentState state, Listener listener) {
        String current = start;
        int hops = 0;
        while (current != null && !END.equals(current)) {
            Node node = nodes.get(current);
            if (node == null) {
                throw new IllegalStateException(
                        "Node '" + current + "' is not reachable — not wired into this graph");
            }
            state = node.run(state);
            if (listener != null) {
                listener.onNode(current, state);
            }
            Route route = routes.get(current);
            current = (route == null) ? END : route.next(state);
            if (++hops > 500) {
                throw new IllegalStateException("Graph did not terminate after 500 hops");
            }
        }
        return state;
    }

    public static final class Builder {

        private final String start;
        private final Map<String, Node> nodes = new LinkedHashMap<>();
        private final Map<String, Route> routes = new LinkedHashMap<>();

        private Builder(String start) {
            this.start = start;
        }

        public Builder node(String name, Node fn) {
            nodes.put(name, fn);
            return this;
        }

        /** Static edge: from → to. */
        public Builder link(String from, String to) {
            routes.put(from, s -> to);
            return this;
        }

        /** Terminal edge: from → END. */
        public Builder end(String from) {
            return link(from, END);
        }

        /** Conditional edge: from → router (reads state only). */
        public Builder branch(String from, Route router) {
            routes.put(from, router);
            return this;
        }

        public Graph build() {
            return new Graph(this);
        }
    }
}