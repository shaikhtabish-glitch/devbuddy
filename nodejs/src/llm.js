/**
 * DevBuddy — OpenRouter LLM Client Factory
 *
 * Uses LangChain's ChatOpenAI pointed at OpenRouter.
 * One client. Any model. Swap by changing a string in config.js.
 */
import { ChatOpenAI } from "@langchain/openai";
import { config } from "./config.js";

/**
 * Return a LangChain chat model pointed at OpenRouter.
 *
 * @param {Object} [opts]
 * @param {string} [opts.model] - OpenRouter model string. Defaults to config.model.
 * @param {number} [opts.temperature] - 0.0 for deterministic, higher for creative.
 * @returns {ChatOpenAI} Configured chat model instance.
 */
export function getLlm(opts = {}) {
  const { model = config.model, temperature = config.defaultTemperature } = opts;

  return new ChatOpenAI({
    model,
    temperature,
    apiKey: config.openRouterApiKey,
    configuration: {
      baseURL: config.openRouterBaseUrl,
      defaultHeaders: {
        "HTTP-Referer": config.appReferer,
        "X-Title": config.appTitle,
      },
    },
  });
}
