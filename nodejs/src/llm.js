/**
 * DevBuddy — OpenRouter LLM Client Factory
 *
 * Uses LangChain's ChatOpenAI pointed at OpenRouter.
 * One client. Any model. Swap by changing a string.
 */
import { ChatOpenAI } from "@langchain/openai";

const OPENROUTER_BASE = "https://openrouter.ai/api/v1";
const DEFAULT_MODEL = "openai/gpt-4o-mini";

/**
 * Return a LangChain chat model pointed at OpenRouter.
 *
 * @param {string} [model] - OpenRouter model string (e.g. "openai/gpt-4o-mini", "anthropic/claude-sonnet").
 *                           Defaults to DEFAULT_MODEL.
 * @param {number} [temperature=0.0] - 0.0 for deterministic, higher for creative.
 * @returns {ChatOpenAI} Configured chat model instance.
 * @throws {Error} If OPENROUTER_API_KEY is not set.
 */
export function getLlm(model = DEFAULT_MODEL, temperature = 0.0) {
  const apiKey = process.env.OPENROUTER_API_KEY;
  if (!apiKey) {
    throw new Error(
      "OPENROUTER_API_KEY not set.\n" +
        "Copy .env.example to .env and add your key."
    );
  }

  return new ChatOpenAI({
    model: model || DEFAULT_MODEL,
    temperature,
    apiKey,
    configuration: {
      baseURL: OPENROUTER_BASE,
      defaultHeaders: {
        "HTTP-Referer": "https://github.com/your-org/devbuddy",
        "X-Title": "DevBuddy",
      },
    },
  });
}
