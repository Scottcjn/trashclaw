# Local LLM Tool Use Benchmark for TrashClaw

TrashClaw operates heavily on autonomous tool execution (file editing, shell commands, semantic search). Not all local models handle these complex instructions equally. 

Below is a benchmark of popular local LLMs tested for their capability to act as the cognitive engine for TrashClaw, focusing on function calling reliability, XML fallback parsing, multi-step orchestration, and edit boundary respect.

## Model Compatibility Matrix

| Model | Native Tool Calling | XML Fallback Parsing | Multi-step Tasks (3+ tools) | Respects File Edit Boundaries | Overall Grade | Notes |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Qwen 2.5 Coder (32B)** | 🟢 Excellent | 🟢 Excellent | 🟢 Excellent | 🟢 Excellent | **S** | The current gold standard for local tool use. Flawlessly orchestrates multi-step workflows and handles complex file editing without hallucinating boundaries. |
| **Qwen 2.5 Coder (14B)** | 🟢 Good | 🟢 Excellent | 🟡 Fair | 🟢 Good | **A-** | Very capable for standard operations. Occasionally struggles to chain more than 3 tools in a single context window without losing track of the final goal. |
| **Qwen 2.5 Coder (7B)** | 🟡 Fair | 🟢 Good | 🔴 Poor | 🟡 Fair | **B-** | Good for single-shot tasks (e.g., "read this file"). Tends to loop or forget parameters during complex multi-step orchestration. |
| **Llama 3.1 (8B Instruct)** | 🔴 Poor | 🟢 Good | 🔴 Poor | 🟡 Fair | **C** | Native tool calling format often breaks or hallucinates schemas. However, it performs decently when forced into the XML fallback parsing mode. |
| **Llama 3.3 (70B Instruct)** | 🟢 Excellent | 🟢 Excellent | 🟢 Good | 🟢 Excellent | **A** | Highly capable and reliable, though slower than Qwen 32B on similar hardware. Great at respecting system prompts and edit boundaries. |
| **DeepSeek Coder V2 (16B)** | 🟢 Good | 🟢 Good | 🟢 Good | 🟢 Excellent | **A-** | Excellent at the actual code editing (replacements/diffs), but can sometimes be stubborn about using tools iteratively instead of trying to write bash scripts to do everything at once. |
| **DeepSeek Coder V2 (Lite)** | 🟡 Fair | 🟡 Fair | 🔴 Poor | 🟡 Fair | **C+** | Often hallucinates tool names or provides malformed JSON arguments when native tool calling is enabled. |
| **Mistral Nemo (12B)** | 🟢 Good | 🟢 Good | 🟡 Fair | 🟡 Fair | **B+** | Solid generalist. Handles basic tool schemas well but struggles with the strict character-matching required for `replace_string` operations. |
| **Mixtral 8x7B Instruct** | 🟡 Fair | 🟢 Good | 🟡 Fair | 🔴 Poor | **C+** | Tends to ignore tool instructions in favor of just printing the code to the user. Requires very strong system prompt constraints. |
| **Phi-3 Mini (3.8B)** | 🔴 Poor | 🟡 Fair | 🔴 Poor | 🔴 Poor | **D** | Too small for reliable agentic workflows. Fails to adhere to JSON schemas and frequently truncates outputs. |

## Evaluation Criteria

1. **Native Tool Calling:** How reliably does the model format its output according to the OpenAI/Ollama tool calling JSON schema without syntax errors?
2. **XML Fallback Parsing:** If native tools fail, can the model reliably fall back to using `<tool_call>` XML tags as instructed in the system prompt?
3. **Multi-step Tasks:** Can the model autonomously execute a sequence of actions (e.g., `search_files` -> `read_file` -> `edit_file`) to solve an ambiguous goal without human intervention?
4. **Respects File Edit Boundaries:** When using editing tools (like `replace_string`), does the model provide exact, unescaped literal text, or does it lazily use `// ... rest of code` placeholders which break the patching mechanism?

## Recommendations for TrashClaw

* **Best Performance (32GB+ RAM):** `qwen2.5-coder:32b` or `llama3.3`
* **Best Balance (16GB RAM):** `deepseek-coder-v2` or `qwen2.5-coder:14b`
* **Best for Low-end Hardware (8GB RAM):** `qwen2.5-coder:7b` (Ensure you use XML fallback mode for better reliability).
