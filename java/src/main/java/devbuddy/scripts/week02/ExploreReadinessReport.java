package devbuddy.scripts.week02;

import devbuddy.schemas.Json;
import devbuddy.schemas.ServiceReadinessReport;

import java.nio.file.Files;
import java.nio.file.Path;

/**
 * Week 2 — Explore: validate a ServiceReadinessReport from mock data.
 *
 * <p>Loads one JSON scenario from {@code shared/data} and validates it against
 * the schema (record constructors enforce the cross-field invariants). No API
 * calls — this is the pure-schema exercise.</p>
 *
 * <p>Run: {@code mvn -q compile exec:java -Dexec.mainClass=devbuddy.scripts.week02.ExploreReadinessReport}</p>
 */
public class ExploreReadinessReport {

    public static void main(String[] args) throws Exception {
        Path path = Path.of("../shared/data/service-readiness-healthy.json");
        String json = Files.readString(path);

        System.out.println("=".repeat(70));
        System.out.println("  ServiceReadinessReport — Reference Validation");
        System.out.println("=".repeat(70));
        System.out.println();
        System.out.println("  Loading " + path + "...");

        ServiceReadinessReport report = Json.parse(json, ServiceReadinessReport.class);

        System.out.println("  ✓ Validated — " + report.getClass().getSimpleName() + "(");
        System.out.println("       service.name    = " + report.service().name());
        System.out.println("       service.version = " + report.service().version());
        System.out.println("       build.status    = " + report.build().status().value());
        System.out.println("       deploy.history  = " + report.deployment().recentDeploys().size() + " deploys");
        System.out.println("       verdict.ready   = " + report.verdict().ready());
        System.out.println("       verdict.conf    = " + report.verdict().confidence().value());
        System.out.println("       blockers        = " + report.verdict().blockers());
        System.out.println("       evidence        = " + report.evidence().size() + " chunks");
        System.out.println("     )");

        // Round-trip through JSON to confirm the contract survives serialization.
        String dumped = Json.toJson(report);
        ServiceReadinessReport reloaded = Json.parse(dumped, ServiceReadinessReport.class);
        System.out.println();
        System.out.println("  ✓ Round-trip OK: " + reloaded.service().name() + " → "
                + (reloaded.verdict().ready() ? "ready" : "not ready"));
    }
}
