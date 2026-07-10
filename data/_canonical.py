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


AA_IMG_NAME_MAP = {
    "Claude Fable 5 (with fallback)":        "claude-fable-5",
    "Claude Opus 4.8 (max)":                 "claude-opus-4.8",
    "Claude Opus 4.7 (max)":                 "claude-opus-4.7",
    "Claude Opus 4.6 (max)":                 "claude-opus-4.6",
    "Claude Opus 4.5":                       "claude-4.5-sonnet-thinking",
    "Claude Sonnet 5 (max)":                "claude-sonnet-5",
    "Claude Sonnet 5 (xhigh)":              "claude-sonnet-5",
    "Claude Sonnet 5 (high)":               "claude-sonnet-5",
    "Claude Sonnet 5 (medium)":             "claude-sonnet-5",
    "Claude Sonnet 5 (low)":                "claude-sonnet-5",
    "Claude 4.5 Sonnet":                    "claude-4.5-sonnet-thinking",
    "GPT-5.5 (xhigh)":                       "gpt-5.5-xhigh",
    "GPT-5.5 (high)":                        "gpt-5.5-high",
    "GPT-5.5 (medium)":                      "gpt-5.5-medium",
    "GPT-5.5 (low)":                         "gpt-5.5-low",
    "GPT-5.4 (xhigh)":                       "gpt-5.4",
    "GPT-5.4 nano":                          "gpt-5-4-nano",
    "GPT-5.4 nano (xhigh)":                  "gpt-5-4-nano",
    "GPT-5.4 mini (xhigh)":                  "gpt-5-4-mini",
    "GPT-5.4 mini (medium)":                 "gpt-5-4-mini",
    "GPT-5.3 Codex (xhigh)":                 "gpt-5.3-codex",
    "GPT-5.2 Codex (xhigh)":                 "gpt-5-2-codex",
    "Gemini 3.1 Pro Preview":                "gemini-3.1-pro-preview",
    "Gemini 3 Pro Preview (high)":           "gemini-3-pro",
    "Gemini 3 Pro Preview (low)":            "gemini-3-pro",
    "Gemini 3 Flash":                        "gemini-3-flash",
    "Gemini 3.5 Flash":                      "gemini-3.5-flash",
    "Gemini 3.5 Flash (medium)":             "gemini-3.5-flash",
    "Gemini 3.1 Flash-Lite":                 "gemini-3-1-flash-lite-preview",
    "Grok 4.3 (high)":                       "grok-4.3",
    "Grok 4.3 (medium)":                     "grok-4.3",
    "Grok 4.3 (low)":                        "grok-4.3",
    "Qwen3.7 Max":                           "qwen3.7-max",
    "Qwen3.7 Plus":                          "qwen3.7-max",
    "Qwen3.6 Max Preview":                   "qwen3-6-max",
    "Qwen3.6 Plus":                          "qwen3-6-plus",
    "Qwen3.6 27B":                           "qwen3-6-27b",
    "Qwen3.6 35B A3B":                       "qwen3-6-35b-a3b",
    "MiniMax-M3":                            "minimax-m3",
    "MiniMax-M2.7":                          "minimax-m2.7",
    "MiniMax-M2.5":                          "minimax-m2.5",
    "MiMo-V2.5-Pro":                         "mimo-v2.5-pro",
    "MiMo-V2.5":                             "mimo-v2.5",
    "MiMo-V2-Pro":                           "mimo-v2-pro",
    "Kimi K2.6":                             "kimi-k2.6",
    "Kimi K2.7 Code":                        "kimi-k2.7-code",
    "Kimi K2 Thinking":                      "kimi-k2-thinking",
    "Kimi K2.5":                             "kimi-k2.5",
    "GLM-5.2 (max)":                         "glm-5.2",
    "GLM-5.1":                               "glm-5.1",
    "GLM-5":                                 "glm-5",
    "Nemotron 3 Ultra":                      "nemotron-3-ultra-550b-a55b",
    "NVIDIA Nemotron 3 Super":               "nemotron-3-super-120b-a12b",
    "NVIDIA Nemotron 3 Nano":                "nemotron-3-nano-omni-30b-a3b",
    "DeepSeek V4 Pro (max)":                 "deepseek-v4-pro",
    "DeepSeek V4 Pro (high)":                "deepseek-v4-pro",
    "DeepSeek V4 Flash (max)":               "deepseek-v4-flash",
    "DeepSeek V4 Flash (high)":              "deepseek-v4-flash",
    "Muse Spark":                            "muse-spark",
    "Hermes 4 405B":                         "hermes-4-llama-3-1-405b-reasoning",
    "Hermes 4 70B":                          "hermes-4-llama-3-1-70b-reasoning",
    "Trinity Large Thinking":                "trinity-large-thinking",
    "Nex-N2-Pro":                            "nex-n2-pro",
    "K-EXAONE":                              "k-exaone",
    "Hy3-preview":                           "hy3-preview",
    "Step 3.7 Flash":                        "step-3-7-flash",
    "Step 3.5 Flash 2603":                   "step-3-5-flash",
    "gpt-oss-120b (high)":                   "gpt-oss-120b",
    "gpt-oss-120b (low)":                    "gpt-oss-120b",
    "gpt-oss-20b (high)":                    "gpt-oss-20b",
    "gpt-oss-20b (low)":                     "gpt-oss-20b",
    "Gemma 4 12B":                           "gemma-4-12b",
    "Gemma 4 26B A4B":                       "gemma-4-26b-a4b",
    "Gemma 4 31B":                           "gemma-4-31b",
    "Gemma 4 E2B":                           "gemma-4-e2b",
    "Gemma 4 E4B":                           "gemma-4-e4b",
    "Reka Flash 3":                          "reka-flash-3",
    "Mercury 2":                             "mercury-2",
    "Nemotron 3 Nano Omni 30B A3B":          "nemotron-3-nano-omni-30b-a3b",
    "Solar Pro 3":                           "solar-pro-3",
    "Solar Open 100B":                       "solar-open-100b-reasoning",
    "EXAONE 4.5 33B":                        "exaone-4-5-33b",
}


def aa_img_name_to_canonical(display_name: str) -> str | None:
    return AA_IMG_NAME_MAP.get(display_name)


# Dirac.run "Cache Hit Rates of Inference" full table (dirac.run/posts/cache-hit-rates-agents).
# Keyed by OpenRouter model-page name "Vendor_Model" (e.g. "DeepSeek_DeepSeek_V4_Pro").
# Joined to our canonical ids via the OpenRouter API id. Only entries that resolve to a
# known canonical model are included; the rest are intentionally omitted (no false joins).
DIRAC_NAME_MAP = {
    "Zai_GLM_5": "glm-5",
    "Qwen_Qwen3_VL_32B_Instruct": "qwen3-vl-32b-instruct",
    "Qwen_Qwen36_35B_A3B": "qwen3-6-35b-a3b",
    "Qwen_Qwen36_27B": "qwen3-6-27b",
    "OpenAI_GPT-41_Nano": "gpt-5-4-nano",
    "xAI_Grok_43": "grok-4-3",
    "Anthropic_Claude_Sonnet_46": "claude-sonnet-4-6",
    "Xiaomi_MiMo-V25-Pro": "mimo-v2-5-pro",
    "Xiaomi_MiMo-V25": "mimo-v2-5",
    "Qwen_Qwen3_Coder_Next": "qwen3-coder-next",
    "Anthropic_Claude_Opus_46": "claude-opus-4-6",
    "Anthropic_Claude_Opus_47": "claude-opus-4-7",
    "MiniMax_MiniMax_M27": "minimax-m2-7",
    "OpenAI_gpt-oss-120b": "gpt-oss-120b",
    "Zai_GLM_47_Flash": "glm-5-1",
    "OpenAI_GPT-51": "gpt-5-1",
    "OpenAI_GPT-54_Mini": "gpt-5-4-mini",
    "Meta_Llama_31_8B_Instruct": "llama-3-1-8b-instruct",
    "Qwen_Qwen35-9B": "qwen3-5-9b",
    "MoonshotAI_Kimi_K25": "kimi-k2-5",
    "Tencent_Hy3_preview": "hy3-preview",
    "OpenAI_GPT-53-Codex": "gpt-5-3-codex",
    "StepFun_Step_35_Flash": "step-3-5-flash",
    "OpenAI_GPT-54_Nano": "gpt-5-4-nano",
    "DeepSeek_DeepSeek_V3_0324": "deepseek-v3-0324",
    "Qwen_Qwen35_397B_A17B": "qwen3-5-397b-a17b",
    "Owl_Alpha": "owl-alpha",
    "DeepSeek_DeepSeek_V4_Pro": "deepseek-v4-pro",
    "OpenAI_GPT-4o-mini": "gpt-4o-mini",
    "Google_Gemini_31_Flash_Lite_Preview": "gemini-3-1-flash-lite-preview",
    "Zai_GLM_45_Air": "glm-4-5-air",
    "Anthropic_Claude_Sonnet_45": "claude-4-5-sonnet-thinking",
    "MiniMax_MiniMax_M25": "minimax-m2-5",
    "Anthropic_Claude_Opus_45": "claude-4-5-opus",
    "Qwen_Qwen3_235B_A22B_Instruct_2507": "qwen3-235b-a22b-instruct-2507",
    "OpenAI_GPT-51_Chat": "gpt-5-1-chat",
    "Google_Gemini_20_Flash": "gemini-2-0-flash",
    "Google_Gemma_4_26B_A4B": "gemma-4-26b-a4b",
    "Google_Gemma_4_31B": "gemma-4-31b",
    "Qwen_Qwen36_35B": "qwen3-6-35b",
}


def dirac_name_to_canonical(model_name: str) -> str | None:
    return DIRAC_NAME_MAP.get(model_name.strip())
