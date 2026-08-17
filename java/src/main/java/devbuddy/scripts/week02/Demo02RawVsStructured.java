package devbuddy.scripts.week02;

import devbuddy.config.AppConfig;
import devbuddy.schemas.BuildCheck;
import devbuddy.schemas.Json;
import devbuddy.service.SchemasService;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;

/**
 * Week 2 — Demo 2: Raw JSON Prompting vs. Native Structured Output.
 *
 * <p>Raw JSON prompting is a polite request. The model tries to comply — but it
 * may add markdown fences, conversational text, or invent field names, and your
 * parser breaks. Native structured output (response_format=json_schema) is a
 * contract: the model is constrained at the token level and cannot return output
 * that violates the schema.</p>
 *
 * <p>Run: {@code mvn -q compile exec:java -Dexec.mainClass=devbuddy.scripts.week02.Demo02RawVsStructured}</p>
 */
public class Demo02RawVsStructured {

    private static final String DIFF = """
            Fix login redirect loop in auth-service (PROJ-421)
            Changed session token validation in src/auth.py lines 42-58.
            Previously expired tokens caused infinite redirect for 15% of users.
            Now returns 401 with clear error. No DB changes. Rollback: revert commit.
            Files: src/auth.py, tests/test_auth.py""";

    public static void main(String[] args) {
        try (var ctx = new AnnotationConfigApplicationContext(AppConfig.class)) {
            ChatClient chatClient = ctx.getBean(ChatClient.class);
            SchemasService schemas = ctx.getBean(SchemasService.class);

            System.out.println("=".repeat(75));
            System.out.println("  DEMO: Raw JSON Prompting (Request) vs. Structured Output (Contract)");
            System.out.println("=".repeat(75));
            System.out.println();
            System.out.println("  THE INPUT (same for both approaches):");
            System.out.println("  " + "-".repeat(55));
            for (String line : DIFF.strip().split("\n")) {
                System.out.println("  | " + line);
            }
            System.out.println("  " + "-".repeat(55));
            System.out.println();

            // ── Approach A: raw prompting — "the request" ─────────────
            System.out.println("=".repeat(75));
            System.out.println("  APPROACH A: Raw JSON Prompting");
            System.out.println("=".repeat(75));
            System.out.println();

            String rawPrompt = """
                    Analyze this code change and return a JSON object with these fields:
                    { "project": "string", "severity": "low|medium|high|critical", "summary": "string", "affected_files": ["string"] }

                    DIFF:
                    """ + DIFF;

            String raw = chatClient.prompt()
                    .user(rawPrompt)
                    .call()
                    .chatResponse().getResult().getOutput().getText();

            System.out.println("  Raw response:");
            for (String line : raw.strip().split("\n")) {
                System.out.println("  | " + line);
            }
            System.out.println();

            System.out.println("  Attempting Json.parse() on the raw text...");
            try {
                BuildCheck parsed = Json.parse(raw, BuildCheck.class);
                System.out.println("  OK (no fences this time) -> severity=" + parsed.severity().value());
            } catch (RuntimeException e) {
                System.out.println("  ✗ PARSE FAILED: " + e.getMessage());
                System.out.println("    A stray ```json fence or a chatty sentence breaks the pipeline.");
            }
            System.out.println();

            // ── Approach B: native structured output — "the contract" ──
            System.out.println("=".repeat(75));
            System.out.println("  APPROACH B: response_format=json_schema (native structured output)");
            System.out.println("=".repeat(75));
            System.out.println();

            BuildCheck result = schemas.analyzePr(
                    "Fix login redirect loop in auth-service", DIFF, 0.0, null);

            System.out.println("  Returned: " + result.getClass().getSimpleName() + " (typed record, not a String)");
            System.out.println("    project:        " + result.project());
            System.out.println("    severity:       " + result.severity().value());
            System.out.println("    summary:        " + result.summary());
            System.out.println("    affected_files: " + result.affectedFiles());
            System.out.println();
            System.out.println("  Raw JSON prompting = hope-based architecture.");
            System.out.println("  Native json_schema = engineering.");
            System.out.println("=".repeat(75));
        }
    }
}
