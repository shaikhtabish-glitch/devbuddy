package devbuddy.config;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.model.ChatModel;
import org.springframework.ai.openai.api.OpenAiApi;
import org.springframework.ai.openai.OpenAiChatModel;
import org.springframework.ai.openai.OpenAiChatOptions;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Spring IoC configuration — wires OpenRouter via Spring AI, no Boot needed.
 *
 * <p>Equivalent to:
 * <ul>
 *   <li>Python: {@code llm.py} — {@code get_llm()} factory</li>
 *   <li>Node.js: {@code llm.js} + {@code config.js}</li>
 * </ul>
 *
 * <p>Bootstrapped in {@code Main.main()} via
 * {@code new AnnotationConfigApplicationContext(AppConfig.class)}.</p>
 */
@Configuration
public class AppConfig {

    private static final Logger log = LoggerFactory.getLogger(AppConfig.class);

        // Spring AI appends /v1/chat/completions to the base URL internally.
    // Setting base to /api/v1 would double-up: /api/v1/v1/chat/completions → 404.
    private static final String OPENROUTER_BASE_URL = "https://openrouter.ai/api";

    @Bean
    public OpenAiApi openAiApi() {
        String apiKey = System.getenv("OPENROUTER_API_KEY");
        if (apiKey == null || apiKey.isBlank()) {
            throw new IllegalStateException(
                    "OPENROUTER_API_KEY environment variable is not set.\n" +
                    "Export it before running:  export OPENROUTER_API_KEY=sk-or-...");
        }
        log.debug("OpenAiApi configured → {}", OPENROUTER_BASE_URL);
        return OpenAiApi.builder()
                .baseUrl(OPENROUTER_BASE_URL)
                .apiKey(apiKey)
                .build();
    }

    @Bean
    public OpenAiChatModel chatModel(OpenAiApi openAiApi) {
        String model = System.getenv().getOrDefault("DEVBUDDY_MODEL", "openai/gpt-4o-mini");
        log.info("Chat model: {} (temperature=0.0)", model);
        return OpenAiChatModel.builder()
                .openAiApi(openAiApi)
                .defaultOptions(OpenAiChatOptions.builder()
                        .model(model)
                        .temperature(0.0)
                        .build())
                .build();
    }

    @Bean
    public ChatClient chatClient(ChatModel chatModel) {
        return ChatClient.builder(chatModel).build();
    }

    /**
     * Expose the resolved model name as a named bean so other components
     * can reference it without re-reading the env var.
     */
    @Bean
    public String modelName() {
        return System.getenv().getOrDefault("DEVBUDDY_MODEL", "openai/gpt-4o-mini");
    }
}
