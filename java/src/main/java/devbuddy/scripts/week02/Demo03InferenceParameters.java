package devbuddy.scripts.week02;

import devbuddy.config.AppConfig;
import devbuddy.schemas.BuildCheck;
import devbuddy.service.SchemasService;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;

/**
 * Week 2 — Demo 3: Inference Parameters (temperature + max_tokens).
 *
 * <p>Same PR. Same schema. Vary temperature and maxTokens to show what changes
 * (judgment) and what holds (validity — the contract).</p>
 *
 * <p>Run: {@code mvn -q compile exec:java -Dexec.mainClass=devbuddy.scripts.week02.Demo03InferenceParameters}</p>
 */
public class Demo03InferenceParameters {

    private static final String PR_TITLE = "Consolidate error handling across user profile module";
    private static final String PR_DIFF = """
            Moved duplicate try/except blocks from 6 profile endpoints into a shared
            error_handler.py decorator. No behavior changes — same errors, same messages.
            Added unit tests for the new decorator. This is prep work for the v2 profiles API.
            Files: src/profiles/error_handler.py (+80, new), src/profiles/views.py (-120),
                   tests/test_error_handler.py (+45, new)""";

    public static void main(String[] args) {
        try (var ctx = new AnnotationConfigApplicationContext(AppConfig.class)) {
            SchemasService schemas = ctx.getBean(SchemasService.class);

            System.out.println("=".repeat(65));
            System.out.println("  Demo 3: Inference Parameters — Temp, Max Tokens");
            System.out.println("=".repeat(65));
            System.out.println();

            // ── Part 1: temperature — content varies, contract holds ──
            System.out.println("-".repeat(65));
            System.out.println("  PART 1: Temperature — same input, 4 temperatures");
            System.out.println("-".repeat(65));
            System.out.println();

            for (double temp : new double[]{0.0, 0.3, 0.7, 1.0}) {
                BuildCheck r = schemas.analyzePr(PR_TITLE, PR_DIFF, temp, 200);
                System.out.printf("  temp=%.1f: severity=%s  summary=\"%s\"%n",
                        temp, r.severity().value(), r.summary());
            }
            System.out.println();
            System.out.println("  Key: json_schema guarantees VALIDITY. Temperature controls JUDGMENT.");
            System.out.println("  So temp=0 is a reproducibility choice (tests, caching, CI) —");
            System.out.println("  not a correctness requirement. The schema is what guarantees validity.");
            System.out.println();

            // ── Part 2: max_tokens — truncation kills structured output ──
            System.out.println("-".repeat(65));
            System.out.println("  PART 2: Max Tokens — cost guard or truncation risk?");
            System.out.println("-".repeat(65));
            System.out.println();

            for (int limit : new int[]{200, 50, 15, 8}) {
                try {
                    BuildCheck r = schemas.analyzePr(PR_TITLE, PR_DIFF, 0.0, limit);
                    System.out.printf("  maxTokens=%3d: ✓ %s%n", limit, r.severity().value());
                } catch (Exception e) {
                    System.out.printf("  maxTokens=%3d: ✗ %s%n", limit,
                            e.getMessage() == null ? e.getClass().getSimpleName()
                                    : e.getMessage().replace("\n", " "));
                }
            }
            System.out.println();
            System.out.println("  maxTokens=200 → safe. maxTokens=8 → truncated, validation fails.");
            System.out.println("  Rule: maxTokens must fit your schema. Measure, don't guess.");
            System.out.println();
            System.out.println("=".repeat(65));
            System.out.println("  Inference parameters are architectural decisions, not knobs.");
            System.out.println("=".repeat(65));
        }
    }
}
