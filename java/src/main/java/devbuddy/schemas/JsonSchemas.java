package devbuddy.schemas;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.ai.openai.api.ResponseFormat;

import java.util.Map;

/**
 * Week 2 — JSON Schemas for native structured output.
 *
 * <p>These schemas are the <em>contract</em> the LLM is constrained to obey.
 * They are written in snake_case to match {@code shared/data/*.json}, the
 * Pydantic models in Python, and the Zod schemas in Node.js.</p>
 *
 * <p>They are passed to OpenAI's {@code response_format: json_schema} (strict
 * mode) so the model <em>cannot</em> return output that violates the schema —
 * the Java equivalent of Python's {@code with_structured_output()} and
 * Node.js's {@code withStructuredOutput()}.</p>
 */
public final class JsonSchemas {

    /** BuildCheck — flat, 4-field PR analysis (in-session exercise). */
    public static final String BUILD_CHECK = """
            {
              "type": "object",
              "properties": {
                "project": { "type": "string" },
                "severity": {
                  "type": "string",
                  "enum": ["low", "medium", "high", "critical"]
                },
                "summary": { "type": "string" },
                "affected_files": {
                  "type": "array",
                  "items": { "type": "string" }
                }
              },
              "required": ["project", "severity", "summary", "affected_files"],
              "additionalProperties": false
            }""";

    /** ServiceReadinessReport — composed, nested schema (self-learning + capstone preview). */
    public static final String SERVICE_READINESS_REPORT = """
            {
              "type": "object",
              "properties": {
                "service": {
                  "type": "object",
                  "properties": {
                    "name": { "type": "string" },
                    "version": { "type": "string" },
                    "owner_team": { "type": "string" }
                  },
                  "required": ["name", "version", "owner_team"],
                  "additionalProperties": false
                },
                "build": {
                  "type": "object",
                  "properties": {
                    "status": {
                      "type": "string",
                      "enum": ["healthy", "degraded", "down", "unknown"]
                    },
                    "last_deploy": { "type": "string" },
                    "failing_since": { "type": ["string", "null"] }
                  },
                  "required": ["status", "last_deploy", "failing_since"],
                  "additionalProperties": false
                },
                "deployment": {
                  "type": "object",
                  "properties": {
                    "recent_deploys": {
                      "type": "array",
                      "items": {
                        "type": "object",
                        "properties": {
                          "sha": { "type": "string" },
                          "author": { "type": "string" },
                          "timestamp": { "type": "string" },
                          "status": {
                            "type": "string",
                            "enum": ["success", "failed", "rolling_back"]
                          }
                        },
                        "required": ["sha", "author", "timestamp", "status"],
                        "additionalProperties": false
                      }
                    },
                    "active_incidents": {
                      "type": "array",
                      "items": { "type": "string" }
                    }
                  },
                  "required": ["recent_deploys", "active_incidents"],
                  "additionalProperties": false
                },
                "verdict": {
                  "type": "object",
                  "properties": {
                    "ready": { "type": "boolean" },
                    "confidence": {
                      "type": "string",
                      "enum": ["low", "medium", "high"]
                    },
                    "blockers": {
                      "type": "array",
                      "items": { "type": "string" }
                    },
                    "recommended_next_steps": {
                      "type": "array",
                      "items": { "type": "string" }
                    }
                  },
                  "required": ["ready", "confidence", "blockers", "recommended_next_steps"],
                  "additionalProperties": false
                },
                "evidence": {
                  "type": "array",
                  "items": {
                    "type": "object",
                    "properties": {
                      "source": {
                        "type": "string",
                        "enum": ["rag", "tool", "user"]
                      },
                      "content": { "type": "string" },
                      "relevance_score": { "type": ["number", "null"] }
                    },
                    "required": ["source", "content", "relevance_score"],
                    "additionalProperties": false
                  }
                }
              },
              "required": ["service", "build", "deployment", "verdict", "evidence"],
              "additionalProperties": false
            }""";

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private JsonSchemas() {
        // utility class
    }

    /**
     * Build an OpenAI {@code response_format: json_schema} (strict) from a
     * snake_case schema string.
     *
     * @param name       schema name (OpenAI requires a name, max 64 chars)
     * @param schemaJson the JSON schema, as text
     */
    public static ResponseFormat responseFormat(String name, String schemaJson) {
        Map<String, Object> schema;
        try {
            schema = MAPPER.readValue(schemaJson, new TypeReference<>() {
            });
        } catch (Exception e) {
            throw new IllegalArgumentException("Invalid JSON schema for " + name, e);
        }
        ResponseFormat.JsonSchema jsonSchema = ResponseFormat.JsonSchema.builder()
                .name(name)
                .strict(true)
                .schema(schema)
                .build();
        return ResponseFormat.builder()
                .type(ResponseFormat.Type.JSON_SCHEMA)
                .jsonSchema(jsonSchema)
                .build();
    }
}
