package devbuddy.tools;

import org.springframework.ai.chat.messages.AssistantMessage;
import org.springframework.ai.chat.messages.SystemMessage;
import org.springframework.ai.chat.messages.UserMessage;
import org.springframework.ai.chat.model.ChatModel;
import org.springframework.ai.chat.model.ChatResponse;
import org.springframework.ai.chat.model.Generation;
import org.springframework.ai.chat.prompt.Prompt;
import org.springframework.ai.chat.metadata.ChatResponseMetadata;
import org.springframework.ai.chat.metadata.Usage;
import org.springframework.ai.openai.OpenAiChatOptions;
import org.springframework.ai.tool.ToolCallback;

import java.util.ArrayList;
import java.util.List;

/**
 * Week 4 — the tool-calling loop over a Spring AI {@link ChatModel}.
 *
 * <p>The model decides; Spring AI's tool-calling manager invokes OUR
 * {@link ToolCallback}s (the application layer) — the model never runs the
 * function. Executions are recorded into the trace (the audit log), and
 * token usage is captured per run (the bill).</p>
 */
public final class ToolLoop {

    private ToolLoop() {
    }

    /** Answer + token usage. Executions are appended by the callbacks into a
     * caller-owned list (the audit trail). */
    public record RunResult(String answer,
                            long inputTokens, long outputTokens, long totalTokens) {
    }

    public static RunResult run(String query, ChatModel model, List<ToolCallback> callbacks) {
        Prompt prompt = new Prompt(
                List.of(
                        new SystemMessage("You are a helpful engineering assistant. You have access to tools " +
                                "that can check service health, deployment history, and active incidents. " +
                                "Use tools when you need live data. Answer directly for general questions."),
                        new UserMessage(query)),
                OpenAiChatOptions.builder()
                        .toolCallbacks(callbacks)
                        .build());

        ChatResponse response = model.call(prompt);
        AssistantMessage out = response.getResult().getOutput();
        String answer = out.getText() == null ? "" : out.getText().strip();

        long in = 0, outTok = 0, total = 0;
        ChatResponseMetadata md = response.getMetadata();
        if (md != null) {
            Usage usage = md.getUsage();
            if (usage != null) {
                in = usage.getPromptTokens();
                outTok = usage.getCompletionTokens();
                total = usage.getTotalTokens();
            }
        }

        return new RunResult(answer, in, outTok, total);
    }

    private static String textOf(AssistantMessage message) {
        return message.getText() == null ? "" : message.getText().strip();
    }
}
