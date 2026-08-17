package devbuddy.scripts.week02;

import devbuddy.config.AppConfig;
import devbuddy.schemas.BuildCheck;
import devbuddy.schemas.Json;
import devbuddy.schemas.JsonSchemas;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.model.ChatResponse;
import org.springframework.ai.openai.OpenAiChatOptions;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;

/**
 * Week 2 — Demo 3: Few-shot — the prompt steers the JUDGMENT, the schema fixes
 * the FORMAT.
 *
 * <p>Same PR. Same schema. Two system prompts: no few-shot (default rubric)
 * vs. with few-shot (two examples recalibrate the rubric). The format stays a
 * valid BuildCheck both times; the judgment (severity) is steered.</p>
 *
 * <p>Run: {@code mvn -q compile exec:java -Dexec.mainClass=devbuddy.scripts.week02.Demo03FewShot}</p>
 */
public class Demo03FewShot {

    private static final String PR_TITLE = "Consolidate error handling across user profile module";
    private static final String PR_DIFF = """
            Moved duplicate try/except blocks from 6 profile endpoints into a shared
            error_handler.py decorator. No behavior changes.
            Files: src/profiles/error_handler.py, src/profiles/views.py""";

    private static final String BASE_PROMPT = """
            You are a code reviewer. Analyze the given PR and return a BuildCheck.
            - severity: 'critical' if it touches auth, payments, or security. 'high' if it changes core logic. 'medium' for feature work. 'low' for docs/typos.
            - summary: one sentence describing what changed and why.
            - affected_files: list the files mentioned in the diff.
            - project: extract the project or service name from the PR context.""";

    private static final String FEW_SHOT_PROMPT = BASE_PROMPT + """

            Here are examples to calibrate severity:
            <example>
            PR: 'Consolidated error handling into a shared decorator across 6 endpoints'
            severity: high — it touches the core request path of every endpoint.
            </example>
            <example>
            PR: 'Updated the README with setup steps'
            severity: low — documentation only.
            </example>""";

    public static void main(String[] args) {
        try (var ctx = new AnnotationConfigApplicationContext(AppConfig.class)) {
            ChatClient chatClient = ctx.getBean(ChatClient.class);
            String model = ctx.getBean("modelName", String.class);

            var options = OpenAiChatOptions.builder()
                    .model(model)
                    .temperature(0.0)
                    .responseFormat(JsonSchemas.responseFormat("build_check", JsonSchemas.BUILD_CHECK))
                    .build();

            System.out.println("=".repeat(70));
            System.out.println("  Demo 3: Few-shot — the prompt steers the JUDGMENT");
            System.out.println("=".repeat(70));
            System.out.println();
            System.out.println("  INPUT (same for both runs): " + PR_TITLE);
            System.out.println();

            BuildCheck r1 = run(chatClient, options, BASE_PROMPT, PR_TITLE, PR_DIFF);
            System.out.println("-".repeat(70));
            System.out.println("  RUN 1: default prompt (no examples)");
            System.out.println("-".repeat(70));
            System.out.println();
            System.out.println("    severity = " + r1.severity().value());
            System.out.println("    summary  = \"" + r1.summary() + "\"");
            System.out.println();

            BuildCheck r2 = run(chatClient, options, FEW_SHOT_PROMPT, PR_TITLE, PR_DIFF);
            System.out.println("-".repeat(70));
            System.out.println("  RUN 2: same prompt + a few-shot example steering severity up");
            System.out.println("-".repeat(70));
            System.out.println();
            System.out.println("    severity = " + r2.severity().value());
            System.out.println("    summary  = \"" + r2.summary() + "\"");
            System.out.println();

            System.out.println("  Same input. Same schema. The FORMAT never changed (both are valid");
            System.out.println("  BuildCheck records). The JUDGMENT changed: medium → high.");
            System.out.println();
            System.out.println("  Key: the schema guarantees the SHAPE; the prompt (few-shot) steers");
            System.out.println("  the CONTENT. Few-shot for format is redundant once you have a schema —");
            System.out.println("  but few-shot for judgment steers what the model decides.");
            System.out.println("=".repeat(70));
        }
    }

    private static BuildCheck run(ChatClient chatClient, OpenAiChatOptions options,
                                  String systemPrompt, String title, String diff) {
        ChatResponse response = chatClient.prompt()
                .system(systemPrompt)
                .user("PR Title: " + title + "\n\nDiff:\n" + diff)
                .options(options)
                .call()
                .chatResponse();
        return Json.parse(Json.stripMarkdownFences(response.getResult().getOutput().getText()), BuildCheck.class);
    }
}
