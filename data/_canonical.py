import re


SLUG_TO_CANONICAL = {
    "gpt-oss-20b":                  "gpt-oss-20b",
    "gpt-oss-120b":                 "gpt-oss-120b",
    "gpt-5-5-low":                  "gpt-5.5-low",
    "gpt-5-5-high":                 "gpt-5.5-high",
    "gpt-5-5-medium":               "gpt-5.5-medium",
    "gpt-5-5":                      "gpt-5.5-xhigh",
    "gpt-5-5-pro":                  "gpt-5.5-pro",
    "gpt-5-3-codex":                "gpt-5.3-codex",
    "gpt-5-2-codex":                "gpt-5.2-codex",
    "gpt-5-4":                      "gpt-5.4",
    "gpt-5-4-high":                 "gpt-5.4-high",
    "gpt-5-5-instant":              "gpt-5.5-instant",
    "claude-opus-4-8":              "claude-opus-4.8",
    "claude-opus-4-6":              "claude-opus-4.6",
    "claude-opus-4-7":              "claude-opus-4.7",
    "claude-4-5-haiku-reasoning":   "claude-4.5-haiku-reasoning",
    "claude-4-5-sonnet-thinking":   "claude-4.5-sonnet-thinking",
    "claude-sonnet-4-6":            "claude-sonnet-4.6",
    "claude-sonnet-4-6-adaptive":   "claude-sonnet-4.6-adaptive",
    "claude-sonnet-4-5-20250929":   "claude-sonnet-4.5",
    "claude-fable-5":               "claude-fable-5",
    "claude-sonnet-5":              "claude-sonnet-5",
    "gemini-3-5-flash":             "gemini-3.5-flash",
    "gemini-3-1-pro-preview":       "gemini-3.1-pro-preview",
    "gemini-3-pro":                 "gemini-3-pro",
    "gemini-3-flash":               "gemini-3-flash",
    "gemma-4-31b":                  "gemma-4-31b",
    "deepseek-v4-pro":              "deepseek-v4-pro",
    "deepseek-v4-flash":            "deepseek-v4-flash",
    "grok-4-3":                     "grok-4.3",
    "grok-4-1":                     "grok-4.1",
    "mistral-medium-3-5":           "mistral-medium-3.5",
    "nova-2-0-pro-reasoning-medium": "nova-2.0-pro-reasoning-medium",
    "minimax-m2-7":                 "minimax-m2.7",
    "minimax-m3":                   "minimax-m3",
    "minimax-m2-5":                 "minimax-m2.5",
    "nvidia-nemotron-3-ultra-550b-a55b":  "nemotron-3-ultra-550b-a55b",
    "nvidia-nemotron-3-super-120b-a12b":  "nemotron-3-super-120b-a12b",
    "kimi-k2-7-code":               "kimi-k2.7-code",
    "kimi-k2-6":                    "kimi-k2.6",
    "kimi-k2-thinking":             "kimi-k2-thinking",
    "k2-think-v2":                  "k2-think-v2",
    "mimo-v2-5-pro":                "mimo-v2.5-pro",
    "glm-5-2":                      "glm-5.2",
    "glm-5-1":                      "glm-5.1",
    "qwen3-5-397b-a17b":            "qwen3.5-397b-a17b",
    "qwen3-7-max":                  "qwen3.7-max",
    "muse-spark":                   "muse-spark",
    "solar-pro-3":                  "solar-pro-3",
}


COSTBD_NAME_MAP = {
    "gpt-oss-20b (high)":              "gpt-oss-20b",
    "DeepSeek V4 Flash (max)":         "deepseek-v4-flash",
    "MiMo-V2.5-Pro (max)":             "mimo-v2.5-pro",
    "DeepSeek V4 Pro (max)":           "deepseek-v4-pro",
    "gpt-oss-120b (high)":             "gpt-oss-120b",
    "MiniMax-M2.7":                    "minimax-m2.7",
    "MiniMax-M3":                      "minimax-m3",
    "Grok 4.3 (high)":                 "grok-4.3",
    "Nova 2.0 Pro Preview (medium)":   "nova-2.0-pro-reasoning-medium",
    "Kimi K2.7 Code":                  "kimi-k2.7-code",
    "GPT-5.5 (low)":                   "gpt-5.5-low",
    "Claude 4.5 Haiku":                "claude-4.5-haiku-reasoning",
    "Nemotron 3 Ultra":                "nemotron-3-ultra-550b-a55b",
    "NVIDIA Nemotron 3 Super":         "nemotron-3-super-120b-a12b",
    "Gemini 3.1 Pro Preview":          "gemini-3.1-pro-preview",
    "Kimi K2.6":                       "kimi-k2.6",
    "Qwen3.5 397B A17B":               "qwen3.5-397b-a17b",
    "Claude 4.5 Sonnet":               "claude-4.5-sonnet-thinking",
    "GPT-5.5 (medium)":                "gpt-5.5-medium",
    "GLM-5.2 (max)":                   "glm-5.2",
    "Gemini 3.5 Flash":                "gemini-3.5-flash",
    "GPT-5.5 (high)":                  "gpt-5.5-high",
    "GPT-5.5 (xhigh)":                 "gpt-5.5-xhigh",
    "Qwen3.7 Max":                     "qwen3.7-max",
    "Claude Sonnet 4.6 (max)":         "claude-sonnet-4.6-adaptive",
    "Mistral Medium 3.5":              "mistral-medium-3.5",
    "Claude Opus 4.8 (max)":           "claude-opus-4.8",
    "Claude Sonnet 5 (max)":           "claude-sonnet-5",
}


def resolve_from_slug(slug: str) -> str:
    return SLUG_TO_CANONICAL.get(slug, slug)


def livebench_name_to_canonical(name: str) -> str:
    n = name.strip().lower()
    n = re.sub(r'-20\d{6}', '', n)
    return resolve_from_slug(n)


def openrouter_id_to_canonical(rid: str) -> str:
    r = rid.strip().lower()
    parts = r.split("/")
    slug = parts[-1] if len(parts) >= 2 else r
    return resolve_from_slug(slug)


def openllm_name_to_canonical(name: str) -> str | None:
    if not name:
        return None
    n = name.strip()
    if "href=" in n:
        m = re.search(r'href="([^"]+)"', n)
        if m:
            n = m.group(1)
    n = n.lower()
    if "/" in n:
        n = n.split("/")[-1]
    n = re.sub(r'-20\d{6}', '', n)
    return resolve_from_slug(n)


OR_ID_MAP = {
    "claude-sonnet-4.6-adaptive":          "anthropic/claude-sonnet-4.6",
    "gemini-3-pro":                        "google/gemini-3-pro",
    "gemini-3-pro-low":                    "google/gemini-3-pro",
    "gemini-3-flash-reasoning":            "google/gemini-3-flash-preview",
    "claude-opus-4-7":                     "anthropic/claude-opus-4",
    "claude-opus-4-6-adaptive":            "anthropic/claude-opus-4",
    "claude-opus-4-5-thinking":            "anthropic/claude-opus-4",
    "deepseek-v4-pro-high":                "deepseek/deepseek-v4-pro",
    "deepseek-v4-flash-high":              "deepseek/deepseek-v4-flash",
    "gpt-5-5-instant-06-26":               "openai/gpt-5.5-instant",
    "claude-4.5-sonnet-thinking":          "anthropic/claude-4.5-sonnet",
    "claude-4.5-haiku-reasoning":          "anthropic/claude-4.5-haiku",
    "grok-4-3-medium":                     "xai/grok-4.3",
    "grok-4-3-low":                        "xai/grok-4.3",
    "gemini-3-5-flash-medium":             "google/gemini-3.5-flash",
    "gpt-oss-120b-low":                    "openai/gpt-oss-120b",
    "gpt-oss-20b-low":                     "openai/gpt-oss-20b",
    "claude-sonnet-5-high":                "anthropic/claude-sonnet-5",
    "gemma-4-26b-a4b":                     "google/gemma-4-26b-a4b-it",
    "gemma-4-31b":                         "google/gemma-4-31b-it",
    "nemotron-3-nano-omni-30b-a3b":        "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
    "nvidia-nemotron-3-nano-30b-a3b-reasoning": "nvidia/nemotron-3-nano-30b-a3b",
    "sonar-reasoning":                     "perplexity/sonar",
    "sonar-reasoning-pro":                 "perplexity/sonar-pro",
    "diffusiongemma-26b-a4b":              "google/fusion",
    "gpt-5.5-xhigh":                       "openai/gpt-5.5",
    "gpt-5.5-high":                        "openai/gpt-5.5",
    "gpt-5.5-medium":                      "openai/gpt-5.5",
    "gpt-5.5-low":                         "openai/gpt-5.5",
    "gpt-5-4":                             "openai/gpt-5",
    "gpt-5-4-mini":                        "openai/gpt-5",
    "gpt-5-4-nano":                        "openai/gpt-5",
    "gpt-5-4-mini-medium":                 "openai/gpt-5",
    "gpt-5-4-nano-medium":                 "openai/gpt-5",
    "kimi-k2-5":                           "moonshot/kimi-k2",
    "kimi-k2-thinking":                    "moonshot/kimi-k2",
}

OR_SUFFIXES = [
    "-thinking", "-high", "-low", "-medium", "-xhigh",
    "-preview", "-reasoning", "-non-thinking", "-it", ":free",
]


def canonical_to_or_id(canonical: str) -> str | None:
    return OR_ID_MAP.get(canonical)


def resolve_or_context(all_models: dict, or_models: list[dict]) -> None:
    or_ctx = {}
    for m in or_models:
        rid = m["id"]
        canonical = openrouter_id_to_canonical(rid)
        ctx = m.get("context_length")
        if ctx is not None and isinstance(ctx, (int, float)) and ctx > 0:
            or_ctx[canonical] = int(ctx)

    for our_slug, or_id in OR_ID_MAP.items():
        if our_slug in all_models:
            canonical = openrouter_id_to_canonical(or_id)
            if canonical in or_ctx:
                all_models[our_slug]["meta"]["context_window"] = or_ctx[canonical]

    for cid in all_models:
        if "context_window" not in all_models[cid].get("meta", {}):
            if cid in or_ctx:
                all_models[cid]["meta"]["context_window"] = or_ctx[cid]
                continue
            for suffix in OR_SUFFIXES:
                stripped = cid
                if suffix in cid:
                    stripped = cid[:-len(suffix)]
                if stripped in or_ctx:
                    all_models[cid]["meta"]["context_window"] = or_ctx[stripped]
                    break


def costbd_name_to_canonical(display_name: str) -> str | None:
    return COSTBD_NAME_MAP.get(display_name)
