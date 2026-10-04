# Ollama Cloud: API notes (accessed 2026-10-04)

Sources were the public docs and pages only. No authenticated calls were made, and no API key was used.

## 1. Base URLs and auth
- OpenAI-compatible base URL for direct cloud access: **`https://ollama.com/v1`**. Docs example: `OpenAI(base_url="https://ollama.com/v1", api_key=os.environ["OLLAMA_API_KEY"])`. Source: https://docs.ollama.com/api/openai-compatibility
- `https://api.ollama.com/v1/...` returns a **301 redirect to `https://ollama.com/v1/...`**, observed with curl. Use `ollama.com/v1` directly.
- Native API base: **`https://ollama.com/api`**, for example `POST https://ollama.com/api/chat`. Source: https://docs.ollama.com/cloud
- Auth header: `Authorization: Bearer $OLLAMA_API_KEY`. Keys are created at https://ollama.com/settings/keys. Source: https://docs.ollama.com/cloud
- The cloud API does not support "stateful Responses, built-in web search through `/v1/responses`, or custom/freeform tool-call replay". Source: https://docs.ollama.com/api/openai-compatibility

## 2. Listing cloud models
- `curl https://ollama.com/api/tags` is the documented method (https://docs.ollama.com/cloud). An **unauthenticated** GET returned HTTP 200. An unauthenticated `GET https://ollama.com/v1/models` also returned 200.
- Model IDs returned on 2026-10-04, verbatim:
  `gpt-oss:20b`, `minimax-m2.7`, `mistral-large-3:675b`, `gpt-oss:120b`, `minimax-m3`, `gemma4:31b`, `kimi-k2.7-code`, `deepseek-v4-pro:0813`, `nemotron-3-nano:30b`, `glm-5.3`, `glm-5.3-flash`, `deepseek-v4.1-flash`, `nemotron-3-ultra`, `kimi-k2.6`, `kimi-k3`, `nemotron-3-super`, `glm-5.2`
- **The cloud listing has no qwen3, qwen3-coder, or kimi-k2 (the original) models, and no deepseek-v3.x models.**

## 3. Free tier (https://ollama.com/pricing)
The new plan model is credit-based. The old hourly/session and weekly limits are gone. The pricing page quotes:
- Free plan: "$0", "Use any cloud model with pay-as-you-go usage credits.", "Starter usage credits included", "Includes access to starter models", "Add credits to unlock all models".
- "Free accounts include a starter amount of usage for a smaller set of starter models. Buying usage credits unlocks all models."
- Reset: "On the Free plan, usage resets monthly from the date you signed up." Unused usage does not roll over.
- Concurrency: "Free includes 1 concurrent request, Pro 3, and Max and Team 10. Requests beyond your plan's concurrency limit are queued and processed as soon as a slot is available. Queued requests are held up to a fixed limit - if the queue is full, the request will be rejected until one of your concurrency slots opens."
- Old limits: "...the session and weekly limits of the old plans no longer apply." This line refers to switching from the old Pro/Max plans.
- Paid plans: Pro costs $20/mo and includes $60 of credits. Max costs $100/mo and includes $300. Team costs $500/mo and includes $1,000. Prices per 1M tokens (input/output): gpt-oss:20b $0.07/$0.30, gpt-oss:120b $0.15/$0.60, glm-5.3-flash $0.15/$0.50, deepseek-v4.1-flash $0.30/$1.20. Off-peak pricing applies on weekdays outside 12:00–18:00 UTC and all day on weekends.
- The page shows no date. The footer says © 2026.
- **Unverified:** which models count as "starter models". The pricing page doesn't list them, and third-party sites disagree.
- **Unverified:** the exact HTTP status when free credits run out or the queue is full. The errors doc lists "`429`: Too Many Requests (e.g. when a rate limit is exceeded)" and "`502`: Bad Gateway (e.g. when a cloud model cannot be reached)". Source: https://docs.ollama.com/api/errors. 429 is the likely status, but the docs don't confirm it for these cases.

## 4. Tool calling per cloud model
- On https://ollama.com/search?c=cloud, **every cloud model family carries the `tools` tag**: deepseek-v4.1-flash, deepseek-v4-pro, glm-5.3, glm-5.3-flash, glm-5.2, minimax-m3, minimax-m2.7, kimi-k3, kimi-k2.7-code, kimi-k2.6, nemotron-3-ultra/super/nano, gemma4, mistral-large-3, and gpt-oss (20b and 120b).
- Pricing FAQ: "Cloud models that are trained to support tools are tested for tool calling and with real agent workflows before they go live."
- `-cloud` suffix: for direct calls to ollama.com, use the exact `/api/tags` name, for example `gemma4:31b`, with no suffix. Through a signed-in local server or the CLI, use the `:cloud`/`-cloud` form, for example `gemma4:cloud`. Source: https://docs.ollama.com/cloud and the openai-compatibility page.
- **Unverified:** whether tool calling works end to end through `/v1` for each model. The tag shows the capability, but nothing was tested.

## 5. OpenAI-compatible `/v1/chat/completions` fields (https://docs.ollama.com/api/openai-compatibility)
- Supported: `tools`, `temperature`, `top_p`, `max_tokens`, `seed`, `stop`, `stream`, `stream_options.include_usage`, `response_format`, `frequency_penalty`, `presence_penalty`, `reasoning_effort` / `reasoning.effort`.
- **Not supported:** `tool_choice`, `logit_bias`, `user`, `n`, and logprobs. Image URLs are not accepted; send images as base64.
- **Caveat on structured outputs:** the structured-outputs doc says "**Ollama's Cloud currently does not support structured outputs.**" It also says structured outputs work through the OpenAI-compatible API via `response_format`, but that applies to local use. Source: https://docs.ollama.com/capabilities/structured-outputs. Plan on JSON-mode prompting plus client-side validation for cloud calls. **Unverified:** whether `response_format: {type: "json_object"}` (JSON mode) works on the cloud.

## 6. Local Ollama
- The local OpenAI-compatible endpoint is `http://localhost:11434/v1/`. The `api_key` is "required but ignored". Source: https://docs.ollama.com/api/openai-compatibility
- On https://ollama.com/library/qwen3, qwen3 has the `tools` and `thinking` tags, and `8b` is a listed size. The tool-calling docs use `qwen3` as their example model (https://docs.ollama.com/capabilities/tool-calling).
- The local Ollama server was **not running** on this machine on 2026-10-04: localhost:11434 did not respond. A local `qwen3:8b` tool call is therefore **unverified**.
