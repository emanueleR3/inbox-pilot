"""
Core workflow nodes for the quiz system.
"""

import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Optional, Dict
from dotenv import load_dotenv

from .config import get_llm, QuizPhases
from .state import QuizState, BulletItem
from automations.quiz.models.llm_response import (
    BulletListItem,
    PlanResponse,
    CollectResponse,
    CollectedInfoItem,
    NewBulletItem,
    ValidationResponse,
    ContextEditResponse,
    BusinessFromContextResponse,
    SingleCategoryPrefillResponse,
    QdrantPrefillResponse,
    SmartContextEditResponse,
)
from automations.quiz.prompts import (
    VALIDATE_BUSINESS_SYSTEM_PROMPT,
    VALIDATE_BUSINESS_USER_PROMPT_TEMPLATE,
    GENERATE_PLAN_SYSTEM_PROMPT,
    GENERATE_PLAN_USER_PROMPT_TEMPLATE,
    PROCESS_ANSWER_SYSTEM_PROMPT,
    PROCESS_ANSWER_USER_PROMPT_TEMPLATE,
    GENERATE_MARKDOWN_SYSTEM_PROMPT,
    GENERATE_MARKDOWN_USER_PROMPT_TEMPLATE,
    REVIEW_CONTEXT_START_MESSAGE,
    EDIT_CONTEXT_SYSTEM_PROMPT,
    EDIT_CONTEXT_USER_PROMPT_TEMPLATE,
    INITIAL_QUESTION,
    WITH_CONTEXT_TODO_MESSAGE,
    QDRANT_BUSINESS_FIELD_SYSTEM_PROMPT,
    QDRANT_BUSINESS_FIELD_USER_PROMPT_TEMPLATE,
    QDRANT_PREFILL_SYSTEM_PROMPT,
    QDRANT_PREFILL_USER_PROMPT_TEMPLATE,
    QDRANT_SINGLE_CATEGORY_SYSTEM_PROMPT,
    QDRANT_SINGLE_CATEGORY_USER_PROMPT_TEMPLATE,
    SMART_CONTEXT_AGENT_SYSTEM_PROMPT,
    SMART_CONTEXT_AGENT_USER_PROMPT_TEMPLATE,
)

from automations.quiz.qdrant_rag import embed_texts, qdrant_search, format_top_chunks

load_dotenv()

# Configure LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "true")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "")
os.environ["LANGCHAIN_ENDPOINT"] = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "corretto_quiz")


# ============================================================================
# Node functions
# ============================================================================

def initial_question_node(state: QuizState) -> QuizState:
    """
    Generate the initial question asking about the business field.
    This is the first question for users who skipped scraping.
    
    Args:
        state: Current quiz state
        
    Returns:
        Updated state with initial question
    """
    print(f"❓ [INITIAL_QUESTION] Generating initial question...")
    
    state["current_response"] = INITIAL_QUESTION
    state["phase"] = QuizPhases.INITIAL_QUESTION
    state["messages"].append({
        "role": "assistant",
        "content": INITIAL_QUESTION
    })
    state["turn_count"] = 1
    
    print(f"   ✅ Initial question generated")
    return state


def validate_business_answer_node(state: QuizState) -> Tuple[QuizState, bool]:
    """
    Validate if the user provided valid information about their business.
    If not valid, ask for clarification without generating a plan.
    
    Args:
        state: Current quiz state
        
    Returns:
        Tuple of (updated state, is_valid)
    """
    print(f"🔍 [VALIDATE_BUSINESS] Validating user's business description...")
    
    # Get the user's answer
    user_answer = state.get("business_field", "")
    if not user_answer:
        for msg in reversed(state["messages"]):
            if msg["role"] == "user":
                user_answer = msg["content"]
                break
    
    print(f"   📝 User answer: {user_answer[:100]}...")
    
    llm = get_llm(temperature=0.1)
    structured_llm = llm.with_structured_output(ValidationResponse, method="function_calling")
    
    user_prompt = VALIDATE_BUSINESS_USER_PROMPT_TEMPLATE.format(
        user_answer=user_answer
    )

    try:
        response: ValidationResponse = structured_llm.invoke([
            {"role": "system", "content": VALIDATE_BUSINESS_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ])
        
        if response.is_valid:
            print(f"   ✅ Business description is valid")
            print(f"   📋 Summary: {response.business_summary}")
            # Store the validated business field
            state["business_field"] = user_answer
            return state, True
        else:
            print(f"   ⚠️ Business description is NOT valid")
            print(f"   ❓ Missing: {response.missing_info}")
            
            # Ask for clarification
            clarification = response.clarification_request or (
                "Non ho capito bene di cosa si occupa la tua azienda.\nPotresti descrivere più nel dettaglio il settore in cui operate e i principali servizi/prodotti che offrite?"
            )
            
            state["current_response"] = clarification
            state["messages"].append({
                "role": "assistant",
                "content": clarification
            })
            state["turn_count"] += 1
            # Stay in INITIAL_QUESTION phase to collect more info
            state["phase"] = QuizPhases.INITIAL_QUESTION
            
            return state, False
            
    except Exception as e:
        print(f"   ❌ Error validating business description: {e}")
        state["error"] = str(e)
        # On error, assume valid and proceed
        return state, True


def generate_plan_node(state: QuizState) -> QuizState:
    """
    After receiving the business field description, generate a bullet list
    of information categories to collect.
    
    Args:
        state: Current quiz state
        
    Returns:
        Updated state with bullet list plan
    """
    print(f"📋 [GENERATE_PLAN] Generating information collection plan...")
    
    # Get the user's business description from the last message
    business_description = state["business_field"]
    
    if not business_description:
        # Find the last user message
        for msg in reversed(state["messages"]):
            if msg["role"] == "user":
                business_description = msg["content"]
                state["business_field"] = business_description
                break
    
    print(f"   📝 Business field: {business_description[:100]}...")

    def _normalize_category_name(name: str) -> str:
        return re.sub(r"\s+", " ", (name or "").strip())

    def _business_sells_products(desc: str) -> bool:
        d = (desc or "").lower()
        product_signals = [
            "e-commerce",
            "ecommerce",
            "shop",
            "store",
            "negozio",
            "vendita",
            "vendiamo",
            "prodotti",
            "articoli",
            "catalogo",
            "ordini",
            "spedizione",
            "spedizioni",
            "consegna",
            "consegne",
            "merce",
            "magazzino",
            "carrello",
        ]
        return any(k in d for k in product_signals)

    def _should_keep_category(name: str, desc: str) -> bool:
        """Generic filter for obviously irrelevant categories.

        We keep this intentionally conservative: only drop categories that
        are clearly out-of-context for many service businesses.
        """
        n = (name or "").strip().lower()

        # Returns / warranty only if the business likely sells products.
        if any(k in n for k in ["reso", "resi", "garanzia", "garanzie", "rimborso", "rimborsi"]):
            return _business_sells_products(desc)

        return True
    
    llm = get_llm(temperature=0.3)
    structured_llm = llm.with_structured_output(PlanResponse, method="function_calling")
    
    user_prompt = GENERATE_PLAN_USER_PROMPT_TEMPLATE.format(
        business_description=business_description
    )

    try:
        response: PlanResponse = structured_llm.invoke([
            {"role": "system", "content": GENERATE_PLAN_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ])
        
        # Convert to state format + normalize + deduplicate + filter
        seen = set()
        bullet_list: List[BulletItem] = []
        for item in response.bullet_list:
            name = _normalize_category_name(item.name)
            if not name:
                continue
            key = name.lower()
            if key in seen:
                continue
            if not _should_keep_category(name, business_description):
                print(f"   🚫 Filtered category (not relevant): {name}")
                continue
            seen.add(key)
            bullet_list.append({"name": name, "completed": False, "info": None})
        
        state["bullet_list"] = bullet_list
        state["current_response"] = response.answer
        state["phase"] = QuizPhases.COLLECTING
        state["messages"].append({
            "role": "assistant",
            "content": response.answer
        })
        state["turn_count"] += 1
        
        print(f"   ✅ Plan generated with {len(bullet_list)} categories")
        for item in bullet_list:
            print(f"      - {item['name']}")
            
    except Exception as e:
        print(f"   ❌ Error generating plan: {e}")
        state["error"] = str(e)
    
    return state


def process_answer_node(state: QuizState) -> QuizState:
    """
    Process the user's answer and update the bullet list accordingly.
    Handles: answers, skips, add items, remove items.
    """
    print(f"💬 [PROCESS_ANSWER] Processing user answer (turn {state['turn_count']})...")
    
    def _normalize_text(text: str) -> str:
        text = (text or "").lower()
        text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _tokenize(text: str) -> List[str]:
        stop = {
            "il", "lo", "la", "i", "gli", "le", "un", "una", "uno",
            "di", "del", "della", "dei", "degli", "delle",
            "a", "ad", "da", "dal", "dalla", "dei", "su", "per", "con", "tra", "fra",
            "e", "o", "ma", "che", "cosa", "come", "quali", "qual", "quando", "dove",
            "anche", "questo", "questa", "punto", "punti",
        }
        tokens = [t for t in _normalize_text(text).split(" ") if t and t not in stop]
        return tokens

    def _best_matching_category(text: str, categories: List[str]) -> Optional[str]:
        """Return the best matching category name for a given text.

        Simple heuristic: token overlap + substring bonus.
        """
        text_norm = _normalize_text(text)
        text_tokens = set(_tokenize(text))

        best_name: Optional[str] = None
        best_score = 0.0

        for cat in categories:
            cat_norm = _normalize_text(cat)
            cat_tokens = set(_tokenize(cat))
            if not cat_tokens:
                continue

            overlap = len(text_tokens & cat_tokens)
            score = float(overlap)
            if cat_norm and cat_norm in text_norm:
                score += 3.0
            elif text_norm and text_norm in cat_norm:
                score += 1.5

            if score > best_score:
                best_score = score
                best_name = cat

        # Require at least a weak signal
        return best_name if best_score >= 1.0 else None

    def _user_wants_remove(text: str) -> bool:
        t = _normalize_text(text)
        return any(k in t for k in ["rimuovi", "rimuovere", "togli", "togliere", "elimina", "eliminare"])

    def _user_wants_remove_many(text: str) -> bool:
        t = _normalize_text(text)
        return any(k in t for k in ["tutti", "tutte", "tutto", "tutta", "punti", "togli tutto", "rimuovi tutto", "elimina tutto"])

    # Get the last user message
    last_user_message = None
    for msg in reversed(state["messages"]):
        if msg["role"] == "user":
            last_user_message = msg["content"]
            break

    # Get last assistant question (helps infer the "current" category)
    last_assistant_message = None
    for msg in reversed(state["messages"]):
        if msg["role"] == "assistant":
            last_assistant_message = msg["content"]
            break
    
    if not last_user_message:
        print(f"   ⚠️ No user message found")
        return state
    
    print(f"   📝 User answer: {last_user_message[:100]}...")

    # Fast-path: user wants to add a new bullet item but didn't provide a name.
    # This avoids relying on the LLM to set needs_name_for_new_item correctly.
    def _wants_add_item_without_name(text: str) -> bool:
        t = (text or "").strip().lower()
        if not t:
            return False
        add_intent = any(k in t for k in ["voglio aggiungere", "aggiungi", "aggiungere"])
        if not add_intent or "punto" not in t:
            return False

        # If they used a clear separator, assume a name is present.
        if ":" in t or "-" in t:
            return False

        tokens = re.split(r"\s+", re.sub(r"[^\w\s]", " ", t))
        stop = {"della", "dell", "del", "di", "da", "alla", "nella", "sulla", "dello", "lista"}
        try:
            idx = tokens.index("punto")
        except ValueError:
            return False
        next_token = tokens[idx + 1] if idx + 1 < len(tokens) else ""
        # If next token is empty or a stopword, there's no explicit name.
        if not next_token or next_token in stop:
            return True
        # If it's just a generic adjective (altro/nuovo), still no name.
        if next_token in {"altro", "nuovo", "ulteriore"}:
            return True
        # Otherwise, assume they provided a name.
        return False

    if _wants_add_item_without_name(last_user_message):
        clarification = "Certo. Come vuoi chiamare il nuovo punto che vuoi aggiungere alla lista?"
        state["current_response"] = clarification
        state["messages"].append({"role": "assistant", "content": clarification})
        state["turn_count"] += 1
        return state
    
    llm = get_llm(temperature=0.2)
    structured_llm = llm.with_structured_output(CollectResponse, method="function_calling")
    
    # Build conversation history - limit to last 4 messages for speed
    history = "\n".join([
        f"{'A' if m['role'] == 'assistant' else 'U'}: {m['content'][:200]}"
        for m in state["messages"][-4:]
    ])
    
    # Build current bullet list status - compact format
    bullet_status = "\n".join([
        f"- {item['name']}: {'✅' if item['completed'] else '❌'}"
        for item in state["bullet_list"]
    ])
    
    user_prompt = PROCESS_ANSWER_USER_PROMPT_TEMPLATE.format(
        business_field=state['business_field'],
        bullet_status=bullet_status,
        history=history
    )

    try:
        response: CollectResponse = structured_llm.invoke([
            {"role": "system", "content": PROCESS_ANSWER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ])
        
        # Build updated bullet list
        updated_bullet_list: List[BulletItem] = []
        removed_this_turn: List[str] = []
        
        # Create maps for quick lookup
        # NOTE: Do not trust response.bullet_list to mass-update completion.
        collected_info_map = {item.category.lower(): item.info for item in response.collected_info}
        skipped_set = {cat.lower() for cat in response.skipped_categories}

        # Guardrail for removals: only remove explicit targets (or current question's category).
        existing_category_names = [item["name"] for item in state["bullet_list"]]
        explicit_remove_target = _best_matching_category(last_user_message or "", existing_category_names) if _user_wants_remove(last_user_message or "") else None
        inferred_current_category = _best_matching_category(last_assistant_message or "", existing_category_names)

        proposed_remove = [c for c in (response.items_to_remove or []) if (c or "").strip()]
        proposed_remove_lower = {c.lower() for c in proposed_remove}

        remove_set: set[str] = set()

        if proposed_remove_lower:
            # If user explicitly mentioned a target, keep only that one (unless user asked to remove many)
            if explicit_remove_target and not _user_wants_remove_many(last_user_message or ""):
                remove_set = {explicit_remove_target.lower()}
            else:
                # Otherwise, allow multiple removals only if user asked for many.
                if _user_wants_remove_many(last_user_message or ""):
                    remove_set = proposed_remove_lower
                else:
                    # Choose a single safest removal: prefer inferred current category if present in proposed list;
                    # otherwise pick the proposed one that best matches the assistant question.
                    if inferred_current_category and inferred_current_category.lower() in proposed_remove_lower:
                        remove_set = {inferred_current_category.lower()}
                    else:
                        best = _best_matching_category(last_assistant_message or "", proposed_remove) or proposed_remove[0]
                        remove_set = {best.lower()}
        else:
            # If user says "remove this point" without naming it, remove only the current category if we can infer it.
            if _user_wants_remove(last_user_message or "") and inferred_current_category:
                remove_set = {inferred_current_category.lower()}
        
        # Process existing items
        for existing in state["bullet_list"]:
            item_name_lower = existing["name"].lower()
            
            # Skip if marked for removal
            if item_name_lower in remove_set:
                print(f"   🗑️ Removed: {existing['name']}")
                removed_this_turn.append(existing["name"])
                continue
            
            # Check if skipped
            is_skipped = item_name_lower in skipped_set

            new_info_raw = collected_info_map.get(item_name_lower)
            new_info = (new_info_raw or "").strip()
            has_new_info = bool(new_info) and new_info.upper() != "SKIP"

            # Guardrail: only mark completed if we truly got info or an explicit skip.
            # Never downgrade completion from True to False.
            completed = bool(existing.get("completed"))
            if is_skipped or (new_info_raw and new_info_raw.upper() == "SKIP"):
                completed = True
            elif has_new_info:
                completed = True

            bullet_item: BulletItem = {
                "name": existing["name"],
                "completed": completed,
                "info": None  # Will be set below
            }
            
            # Handle info
            if is_skipped:
                bullet_item["info"] = None  # Explicitly null for skipped
                print(f"   ⏭️ Skipped: {existing['name']}")
            else:
                if new_info_raw and new_info_raw.upper() != "SKIP" and new_info:
                    existing_info = existing.get("info")
                    if existing_info and new_info.lower() not in existing_info.lower():
                        bullet_item["info"] = f"{existing_info.rstrip()} {new_info}"
                    else:
                        bullet_item["info"] = new_info
                elif existing.get("info"):
                    bullet_item["info"] = existing["info"]
            
            updated_bullet_list.append(bullet_item)
        
        # Add new items (or update existing category if the name matches)
        existing_names_lower = [item["name"].lower() for item in updated_bullet_list]
        existing_index = {item["name"].lower(): i for i, item in enumerate(updated_bullet_list)}

        for new_item in response.items_to_add:
            proposed_name = (new_item.name or "").strip()
            if not proposed_name:
                continue

            proposed_lower = proposed_name.lower()

            # Exact match first
            matched_lower = proposed_lower if proposed_lower in existing_index else None

            # Fallback: single substring match (e.g. "prezzi e preventivi" -> "prezzi")
            if matched_lower is None:
                candidates = [n for n in existing_names_lower if (n in proposed_lower) or (proposed_lower in n)]
                if len(candidates) == 1:
                    matched_lower = candidates[0]

            if matched_lower is not None:
                idx = existing_index[matched_lower]
                if new_item.info:
                    updated_bullet_list[idx]["info"] = new_item.info
                    updated_bullet_list[idx]["completed"] = True
                print(f"   ✏️ Updated existing: {updated_bullet_list[idx]['name']}")
                continue

            print(f"   ➕ Added: {proposed_name}")
            updated_bullet_list.append({
                "name": proposed_name,
                "completed": bool(new_item.info),
                "info": new_item.info
            })
        
        state["bullet_list"] = updated_bullet_list
        def _next_incomplete_category(items: List[BulletItem]) -> Optional[str]:
            for it in items:
                if not it.get("completed"):
                    return it.get("name")
            return None

        def _fallback_next_question(items: List[BulletItem]) -> str:
            next_cat = _next_incomplete_category(items)
            if next_cat:
                return (
                    f"Perfetto. Ora mi serve completare la sezione: {next_cat}.\n\n"
                    "Per aiutarmi, nella risposta includi se puoi:\n"
                    "- Cosa include esattamente (dettagli e varianti)\n"
                    "- Per chi è pensato / a chi si rivolge\n"
                    "- Eventuali condizioni, limiti, prerequisiti o documenti richiesti\n"
                    "- Esempi pratici o casi tipici (se ci sono)\n"
                    "- Qualsiasi nota importante che i clienti chiedono spesso"
                )
            return "Perfetto, direi che abbiamo completato tutto."

        proposed_answer = response.answer or ""
        proposed_answer_norm = _normalize_text(proposed_answer)

        removed_names = removed_this_turn
        removed_match = _best_matching_category(proposed_answer, removed_names) if removed_names else None

        # If the model repeats the exact same question, force progress.
        is_repeat = bool(last_assistant_message) and _normalize_text(last_assistant_message) == proposed_answer_norm

        # If the model is asking about a category that no longer exists, force progress.
        existing_names_now = [it["name"] for it in updated_bullet_list]
        asked_category = _best_matching_category(proposed_answer, existing_names_now)
        refers_to_missing_category = (not asked_category) and bool(proposed_answer_norm)

        should_override_question = bool(remove_set) or bool(removed_this_turn) or is_repeat or bool(removed_match) or refers_to_missing_category

        if response.needs_name_for_new_item:
            final_answer = (proposed_answer or "").strip() or "Come vuoi chiamare il nuovo punto che vuoi aggiungere alla lista?"
        elif should_override_question or not (proposed_answer or "").strip():
            final_answer = _fallback_next_question(updated_bullet_list)
        else:
            final_answer = proposed_answer

        state["current_response"] = final_answer
        state["messages"].append({
            "role": "assistant",
            "content": final_answer
        })
        state["turn_count"] += 1
        
        # Check if all completed (do not trust model-provided all_completed)
        if updated_bullet_list and all(item["completed"] for item in updated_bullet_list):
            state["is_done"] = True
            state["phase"] = QuizPhases.COMPLETED
            print(f"   🎉 All categories completed!")
        
        completed_count = sum(1 for item in updated_bullet_list if item["completed"])
        print(f"   ✅ Progress: {completed_count}/{len(updated_bullet_list)} categories completed")
        
    except Exception as e:
        print(f"   ❌ Error processing answer: {e}")
        state["error"] = str(e)
    
    return state


def check_completion_node(state: QuizState) -> QuizState:
    """
    Check if the quiz should end (all items completed or max turns reached).
    
    Args:
        state: Current quiz state
        
    Returns:
        Updated state
    """
    print(f"🔄 [CHECK_COMPLETION] Checking completion status...")
    
    # Check max turns
    if state["turn_count"] >= state["max_turns"]:
        print(f"   ⚠️ Max turns ({state['max_turns']}) reached")
        state["is_done"] = True
        state["phase"] = QuizPhases.COMPLETED
        return state
    
    # Check if all items are completed
    all_completed = all(item["completed"] for item in state["bullet_list"])
    if all_completed and state["bullet_list"]:
        print(f"   ✅ All {len(state['bullet_list'])} categories completed")
        state["is_done"] = True
        state["phase"] = QuizPhases.COMPLETED
    else:
        completed_count = sum(1 for item in state["bullet_list"] if item["completed"])
        print(f"   📊 Progress: {completed_count}/{len(state['bullet_list'])} completed")
    
    return state


def generate_markdown_node(state: QuizState) -> QuizState:
    """
    Generate the final markdown document with all collected information.
    """
    print(f"📄 [GENERATE_MARKDOWN] Generating final markdown document...")
    
    llm = get_llm(temperature=0.2)
    
    # Build collected information - only items with info
    collected_info = "\n".join([
        f"### {item['name']}\n{item.get('info', 'Non configurato')}\n"
        for item in state["bullet_list"]
    ])
    
    user_prompt = GENERATE_MARKDOWN_USER_PROMPT_TEMPLATE.format(
        business_field=state['business_field'],
        collected_info=collected_info
    )

    try:
        response = llm.invoke([
            {"role": "system", "content": GENERATE_MARKDOWN_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ])
        
        markdown_content = response.content if hasattr(response, 'content') else str(response)
        state["final_markdown"] = markdown_content
        
        print(f"   ✅ Markdown generated ({len(markdown_content)} chars)")
        
    except Exception as e:
        print(f"   ❌ Error generating markdown: {e}")
        state["error"] = str(e)
        # Fallback: create basic markdown from collected info
        state["final_markdown"] = f"# Profilo Aziendale\n\n## Settore\n{state['business_field']}\n\n{collected_info}"
    
    return state


def with_context_node(state: QuizState) -> QuizState:
    """
    Handle the case where user has a qdrant collection (did scraping).
    TODO: Implement RAG-based quiz flow using the scraped context.
    
    Args:
        state: Current quiz state
        
    Returns:
        Updated state
    """
    print(f"🔮 [WITH_CONTEXT] User has qdrant collection: {state['qdrant_collection_name']}")

    collection_name = state.get("qdrant_collection_name")
    if not collection_name:
        # Safety fallback: if collection is missing, behave like no-context flow.
        state["has_qdrant_collection"] = False
        return initial_question_node(state)

    def _normalize_category_name(name: str) -> str:
        return re.sub(r"\s+", " ", (name or "").strip())

    def _business_sells_products(desc: str) -> bool:
        d = (desc or "").lower()
        product_signals = [
            "e-commerce",
            "ecommerce",
            "shop",
            "store",
            "negozio",
            "vendita",
            "vendiamo",
            "prodotti",
            "articoli",
            "catalogo",
            "ordini",
            "spedizione",
            "spedizioni",
            "consegna",
            "consegne",
            "merce",
            "magazzino",
            "carrello",
        ]
        return any(k in d for k in product_signals)

    def _should_keep_category(name: str, desc: str) -> bool:
        n = (name or "").strip().lower()
        if any(k in n for k in ["reso", "resi", "garanzia", "garanzie", "rimborso", "rimborsi"]):
            return _business_sells_products(desc)
        return True

    # 1) Retrieve generic chunks and infer business field
    try:
        seed_query = (
            "Descrizione azienda, servizi offerti, prodotti, settori, come funziona, contatti e orari"
        )
        seed_vec = embed_texts([seed_query])[0]
        seed_results = qdrant_search(collection_name=collection_name, vector=seed_vec, limit=10)
        seed_chunks = format_top_chunks(seed_results, max_chunks=10)
    except Exception as e:
        state["error"] = f"Qdrant search failed: {e}"
        return initial_question_node(state)

    try:
        llm = get_llm(temperature=0.1)
        structured_llm = llm.with_structured_output(BusinessFromContextResponse, method="function_calling")
        user_prompt = QDRANT_BUSINESS_FIELD_USER_PROMPT_TEMPLATE.format(
            chunks="\n\n".join([f"- {c}" for c in seed_chunks])
        )
        business_resp: BusinessFromContextResponse = structured_llm.invoke([
            {"role": "system", "content": QDRANT_BUSINESS_FIELD_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ])
        business_field = (business_resp.business_field or "").strip()
    except Exception as e:
        state["error"] = f"Business extraction failed: {e}"
        return initial_question_node(state)

    if not business_field:
        # If the model returned empty, fall back to letting the user describe it.
        return initial_question_node(state)

    state["business_field"] = business_field

    # STEP 1 COMPLETE: Ask user to confirm the business field
    # User will respond, then we continue with plan generation + RAG in confirm_business_and_continue_node
    confirmation_message = (
        f"Ho visto che vi occupate di: **{business_field}**\n\n"
        "È corretto? Puoi:\n"
        "- Rispondere **sì** per confermare\n"
        "- Rispondere **no** per descrivere tu l'attività\n"
        "- Aggiungere dettagli o correzioni"
    )
    
    state["phase"] = QuizPhases.CONFIRMING_BUSINESS
    state["current_response"] = confirmation_message
    state["messages"].append({"role": "assistant", "content": confirmation_message})
    state["turn_count"] = 1
    
    return state


def confirm_business_and_continue_node(state: QuizState, user_response: str) -> QuizState:
    """
    Process user's response to business field confirmation and continue with RAG retrieval.
    
    Args:
        state: Current quiz state
        user_response: User's response (yes/no/additions)
        
    Returns:
        Updated state
    """
    print(f"🔄 [CONFIRM_BUSINESS] Processing user response...")
    
    normalized = (user_response or "").strip().lower()

    # Robust intent detection: do NOT treat "no" inside "non" as a rejection.
    # - Reject only if the message *starts* with an explicit negative.
    # - If the message contains an explicit "sì/ok/confermo", we treat it as confirmation
    #   even if it contains "non" in the business description.
    positive_re = re.compile(r"\b(sì|si|yes|ok|corretto|esatto|confermo|giusto)\b", re.IGNORECASE)
    negative_start_re = re.compile(
        r"^\s*(no\b|sbagliat[oa]\b|errat[oa]\b|non\s+confermo\b|non\s+è\s+corretto\b|non\s+corretto\b|non\s+esatto\b|non\s+giusto\b)",
        re.IGNORECASE,
    )

    is_affirmative = bool(positive_re.search(normalized))
    is_negative = bool(negative_start_re.search(normalized))

    # If user explicitly rejects, fall back to manual description
    if is_negative and not is_affirmative:
        print("   ❌ User rejected - falling back to manual description")
        state["business_field"] = None
        return initial_question_node(state)

    # Check if user wants to add/correct info
    is_simple_yes = normalized in ["sì", "si", "yes", "ok", "corretto", "esatto", "confermo", "giusto"]
    
    if not is_simple_yes:
        # User provided additional info - update business field
        current_business = state.get("business_field") or ""
        state["business_field"] = f"{current_business}. {user_response}"
        print(f"   ✏️ Updated business field with additions: {state['business_field'][:100]}...")
    else:
        print(f"   ✅ User confirmed business field")
    
    # Now continue with plan generation and RAG retrieval
    collection_name = state.get("qdrant_collection_name")
    business_field = state["business_field"]
    
    def _normalize_category_name(name: str) -> str:
        return re.sub(r"\s+", " ", (name or "").strip())

    def _business_sells_products(desc: str) -> bool:
        d = (desc or "").lower()
        product_signals = [
            "e-commerce", "ecommerce", "shop", "store", "negozio", "vendita",
            "vendiamo", "prodotti", "articoli", "catalogo", "ordini",
            "spedizione", "spedizioni", "consegna", "consegne", "merce", "magazzino", "carrello",
        ]
        return any(k in d for k in product_signals)

    def _should_keep_category(name: str, desc: str) -> bool:
        n = (name or "").strip().lower()
        if any(k in n for k in ["reso", "resi", "garanzia", "garanzie", "rimborso", "rimborsi"]):
            return _business_sells_products(desc)
        return True

    # Generate plan (categories)
    try:
        llm_plan = get_llm(temperature=0.2)
        structured_plan = llm_plan.with_structured_output(PlanResponse, method="function_calling")
        plan_prompt = GENERATE_PLAN_USER_PROMPT_TEMPLATE.format(business_description=business_field)
        plan_resp: PlanResponse = structured_plan.invoke([
            {"role": "system", "content": GENERATE_PLAN_SYSTEM_PROMPT},
            {"role": "user", "content": plan_prompt},
        ])

        seen = set()
        bullet_list: List[BulletItem] = []
        for item in plan_resp.bullet_list:
            name = _normalize_category_name(item.name)
            if not name:
                continue
            key = name.lower()
            if key in seen:
                continue
            if not _should_keep_category(name, business_field):
                continue
            seen.add(key)
            bullet_list.append({"name": name, "completed": False, "info": None})

        state["bullet_list"] = bullet_list
    except Exception as e:
        state["error"] = f"Plan generation failed: {e}"
        return initial_question_node(state)

    if not state["bullet_list"]:
        return initial_question_node(state)

    categories = [it["name"] for it in state["bullet_list"]]
    
    # IMPROVED RAG: Build better queries with category-specific keywords
    def _build_category_query(cat: str, business: str) -> str:
        """Build a more specific query for each category with keyword hints."""
        cat_lower = cat.lower()
        
        # Category-specific keyword boosting
        keyword_map = {
            "contatti": "telefono email indirizzo numero cellulare pec form contatto",
            "orari": "orario apertura chiusura lunedì martedì mercoledì giovedì venerdì sabato domenica ore",
            "prezzi": "prezzo costo tariffa euro listino preventivo quota pagamento",
            "tariffe": "prezzo costo tariffa euro listino preventivo quota pagamento",
            "formazione": "formazione corso certificazione diploma laurea qualifica addestramento",
            "testimonianze": "recensione opinione testimonianza feedback commento cliente soddisfatto",
            "referenze": "recensione opinione testimonianza feedback commento cliente soddisfatto",
        }
        
        # Find matching keywords
        extra_keywords = ""
        for key, keywords in keyword_map.items():
            if key in cat_lower:
                extra_keywords = keywords
                break
        
        if extra_keywords:
            return f"{cat} {extra_keywords}"
        else:
            return f"{business} {cat}"
    
    category_queries = [_build_category_query(cat, business_field) for cat in categories]
    
    try:
        vectors = embed_texts(category_queries)
        chunks_by_category: Dict[str, List[str]] = {}
        for cat, vec in zip(categories, vectors):
            results = qdrant_search(collection_name=collection_name, vector=vec, limit=5)
            chunks_by_category[cat] = format_top_chunks(results, max_chunks=5)
    except Exception as e:
        state["error"] = f"Category retrieval failed: {e}"
        state["phase"] = QuizPhases.COLLECTING
        state["is_done"] = False
        state["current_response"] = (
            f"Perfetto! Iniziamo a raccogliere le informazioni.\n\n"
            f"Partiamo da: **{categories[0]}**.\n\n"
            "Per aiutarmi, includi se puoi:\n"
            "- Dettagli specifici\n"
            "- Varianti / opzioni\n"
            "- Condizioni e requisiti\n"
            "- Esempi pratici"
        )
        state["messages"].append({"role": "assistant", "content": state["current_response"]})
        state["turn_count"] += 1
        return state

    # PARALLEL LLM calls for extraction
    chunk_labels = ["PRIMO CHUNK", "SECONDO CHUNK", "TERZO CHUNK", "QUARTO CHUNK", "QUINTO CHUNK"]

    def _format_chunks_for_category(cat: str) -> str:
        cat_chunks = chunks_by_category.get(cat) or []
        if not cat_chunks:
            return "(nessun estratto rilevante)"
        lines = []
        for idx, chunk_text in enumerate(cat_chunks):
            label = chunk_labels[idx] if idx < len(chunk_labels) else f"CHUNK {idx + 1}"
            lines.append(f"{label}: {chunk_text}")
            lines.append("")
        return "\n".join(lines).strip()

    def _extract_single_category(cat: str) -> Tuple[str, bool, Optional[str]]:
        try:
            llm = get_llm(temperature=0.1)
            structured_llm = llm.with_structured_output(SingleCategoryPrefillResponse, method="function_calling")
            chunks_text = _format_chunks_for_category(cat)
            user_prompt = QDRANT_SINGLE_CATEGORY_USER_PROMPT_TEMPLATE.format(
                category=cat,
                chunks=chunks_text,
            )
            resp: SingleCategoryPrefillResponse = structured_llm.invoke([
                {"role": "system", "content": QDRANT_SINGLE_CATEGORY_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ])
            info = (resp.info.strip() if isinstance(resp.info, str) and resp.info.strip() else None)
            return (cat, bool(resp.completed), info)
        except Exception as e:
            print(f"   ⚠️ Error extracting category '{cat}': {e}")
            return (cat, False, None)

    print(f"   🚀 Starting parallel extraction for {len(categories)} categories...")
    results_map: Dict[str, Tuple[bool, Optional[str]]] = {}

    try:
        with ThreadPoolExecutor(max_workers=min(len(categories), 10)) as executor:
            futures = {executor.submit(_extract_single_category, cat): cat for cat in categories}
            for future in as_completed(futures):
                cat_name, completed, info = future.result()
                results_map[cat_name] = (completed, info)
                status = "✅" if completed else "❌"
                print(f"   {status} {cat_name}: {'extracted' if info else 'no info'}")
    except Exception as e:
        state["error"] = f"Parallel extraction failed: {e}"
        first_cat = categories[0]
        state["phase"] = QuizPhases.COLLECTING
        state["is_done"] = False
        state["current_response"] = (
            f"Perfetto! Iniziamo a raccogliere le informazioni.\n\n"
            f"Partiamo da: **{first_cat}**.\n\n"
            "Per aiutarmi, includi se puoi:\n"
            "- Dettagli specifici\n"
            "- Varianti / opzioni\n"
            "- Condizioni e requisiti\n"
            "- Esempi pratici"
        )
        state["messages"].append({"role": "assistant", "content": state["current_response"]})
        state["turn_count"] += 1
        return state

    # Build updated bullet list from parallel results
    updated: List[BulletItem] = []
    for it in state["bullet_list"]:
        cat_name = it["name"]
        if cat_name in results_map:
            completed, info = results_map[cat_name]
            updated.append({
                "name": cat_name,
                "completed": completed,
                "info": info,
            })
        else:
            updated.append(it)
    state["bullet_list"] = updated

    # Determine completion and generate appropriate response
    all_completed = bool(updated) and all(i.get("completed") for i in updated)
    first_incomplete = next((i["name"] for i in updated if not i.get("completed")), None)

    if all_completed:
        proposed_answer = (
            "Ho estratto queste informazioni dal sito. Controlla se sono corrette e complete, "
            "poi dimmi se vuoi modificare qualcosa oppure scrivi 'OK, salva'."
        )
        state["messages"].append({"role": "assistant", "content": proposed_answer})
        state["turn_count"] += 1
        state["is_done"] = True
        state["phase"] = QuizPhases.COMPLETED
        state = generate_markdown_node(state)
        state = start_review_context_node(state)
        return state
    else:
        proposed_answer = (
            f"Ho recuperato alcune informazioni dal sito.\n\n"
            f"Per completare il profilo, mi servono dettagli su: **{first_incomplete}**.\n\n"
            "Per aiutarmi, includi se puoi:\n"
            "- Dettagli specifici\n"
            "- Varianti / opzioni\n"
            "- Condizioni e requisiti\n"
            "- Esempi pratici"
        )
        state["phase"] = QuizPhases.COLLECTING
        state["is_done"] = False
        state["current_response"] = proposed_answer
        state["messages"].append({"role": "assistant", "content": proposed_answer})
        state["turn_count"] += 1
        return state


def start_review_context_node(state: QuizState) -> QuizState:
    """Start the post-quiz review chat showing the saved markdown and asking for edits/confirmation."""
    state["phase"] = QuizPhases.REVIEWING
    state["is_done"] = False
    state["turn_count"] = 0
    state["max_turns"] = 30

    state["current_response"] = REVIEW_CONTEXT_START_MESSAGE
    state["messages"].append({
        "role": "assistant",
        "content": REVIEW_CONTEXT_START_MESSAGE,
    })
    return state


def _is_confirmation_message(text: str) -> bool:
    normalized = (text or "").strip().lower()
    if not normalized:
        return False
    # Keep it strict to avoid accidental confirmations
    patterns = [
        r"^ok\s*,?\s*salva\.?$",
        r"^ok\s+salva\.?$",
        r"^confermo\.?$",
        r"^va\s+bene\s*,?\s*salva\.?$",
        r"^perfetto\s*,?\s*salva\.?$",
    ]
    return any(re.match(p, normalized) for p in patterns)


def _looks_like_full_markdown(text: str) -> bool:
    t = (text or "").lstrip()
    if len(t) < 80:
        return False
    return t.startswith("#") or ("\n## " in t) or ("\n### " in t)


def smart_context_edit_node(state: QuizState, user_message: str) -> QuizState:
    """
    Smart agent for editing context when user has qdrant_collection.
    
    This agent:
    - Detects intent (add/modify/remove/confirm/clarify)
    - Tracks ALL changes in conversation_log with full detail
    - Handles conflicts by asking user which info to keep
    - Sets pending_context_save flag when user confirms
    
    Args:
        state: Current quiz state
        user_message: User's message
        
    Returns:
        Updated state with tracked changes
    """
    from datetime import datetime
    
    print(f"🧠 [SMART_CONTEXT_EDIT] Processing with smart agent...")
    
    # Max turns check
    if state["turn_count"] >= state["max_turns"]:
        state["context_confirmed"] = True
        state["is_done"] = True
        state["phase"] = QuizPhases.COMPLETED
        state["pending_context_save"] = True
        log_entry = f"[{datetime.now().isoformat()}] [MAX_TURNS] Raggiunto limite massimo di modifiche"
        state["conversation_log"].append(log_entry)
        state["current_response"] = "Ho raggiunto il numero massimo di modifiche. Ho salvato l'ultima versione disponibile."
        state["messages"].append({"role": "assistant", "content": state["current_response"]})
        return state

    # Fast path: explicit confirmation
    if _is_confirmation_message(user_message):
        state["context_confirmed"] = True
        state["is_done"] = True
        state["phase"] = QuizPhases.COMPLETED
        state["pending_context_save"] = True
        log_entry = f"[{datetime.now().isoformat()}] [CONFIRM] L'utente ha confermato il salvataggio del contesto"
        state["conversation_log"].append(log_entry)
        state["current_response"] = "Perfetto. Ho salvato il contesto aziendale definitivo."
        state["messages"].append({"role": "assistant", "content": state["current_response"]})
        return state

    # Fast path: user pasted full markdown replacement
    if _looks_like_full_markdown(user_message):
        old_markdown = state.get("final_markdown") or ""
        state["final_markdown"] = user_message.strip()
        log_entry = f"[{datetime.now().isoformat()}] [REPLACE] L'utente ha sostituito l'intero markdown. Lunghezza precedente: {len(old_markdown)} caratteri, nuova lunghezza: {len(user_message)} caratteri"
        state["conversation_log"].append(log_entry)
        state["current_response"] = (
            "Ricevuto. Ho aggiornato il testo con la tua versione. "
            "Se è tutto corretto scrivi: \"OK, salva\"."
        )
        state["messages"].append({"role": "assistant", "content": state["current_response"]})
        state["turn_count"] += 1
        return state

    # Use LLM for smart intent detection and change tracking
    llm = get_llm(temperature=0.2)
    structured_llm = llm.with_structured_output(SmartContextEditResponse, method="function_calling")

    current_markdown = state.get("final_markdown") or ""
    conversation_log_text = "\n".join(state.get("conversation_log", [])) or "(Nessuna modifica precedente)"
    
    user_prompt = SMART_CONTEXT_AGENT_USER_PROMPT_TEMPLATE.format(
        current_markdown=current_markdown,
        conversation_log=conversation_log_text,
        user_request=user_message,
    )

    try:
        response: SmartContextEditResponse = structured_llm.invoke([
            {"role": "system", "content": SMART_CONTEXT_AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ])

        print(f"   Intent: {response.intent}")
        print(f"   Conflict: {response.conflict_detected}")
        print(f"   Log entry: {response.change_log_entry[:100]}...")

        # Track the change in conversation_log
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] {response.change_log_entry}"
        state["conversation_log"].append(log_entry)

        # Apply the update (unless conflict detected)
        if response.conflict_detected:
            # Don't update markdown, ask user to resolve conflict
            state["current_response"] = response.answer
            print(f"   ⚠️ Conflict detected: {response.conflict_details}")
        else:
            # Apply the markdown update
            state["final_markdown"] = (response.updated_markdown or current_markdown).strip()
            state["current_response"] = response.answer

        # Check if user confirmed
        if response.is_confirmed:
            state["context_confirmed"] = True
            state["is_done"] = True
            state["phase"] = QuizPhases.COMPLETED
            state["pending_context_save"] = True

        state["messages"].append({"role": "assistant", "content": state["current_response"]})
        state["turn_count"] += 1
        return state

    except Exception as e:
        print(f"   ❌ Error in smart context edit: {e}")
        state["error"] = str(e)
        state["current_response"] = "Non sono riuscito ad applicare la modifica. Puoi riprovare in modo più specifico?"
        state["messages"].append({"role": "assistant", "content": state["current_response"]})
        state["turn_count"] += 1
        return state


def edit_context_node(state: QuizState, user_message: str) -> QuizState:
    """
    Apply user edits to the markdown context until they confirm it can be saved.
    
    For users with qdrant_collection (who did scraping), uses the smart context agent
    that tracks all changes in detail for later JSON update.
    
    Args:
        state: Current quiz state
        user_message: User's message
        
    Returns:
        Updated state
    """
    # Use smart agent for users with qdrant collection
    if state.get("has_qdrant_collection"):
        return smart_context_edit_node(state, user_message)
    
    # Original logic for users without qdrant collection
    # Max 30 user turns in this review chat
    if state["turn_count"] >= state["max_turns"]:
        state["context_confirmed"] = True
        state["is_done"] = True
        state["phase"] = QuizPhases.COMPLETED
        state["current_response"] = "Ho raggiunto il numero massimo di modifiche. Ho salvato l'ultima versione disponibile."
        state["messages"].append({"role": "assistant", "content": state["current_response"]})
        return state

    # Fast path: explicit confirmation without LLM
    if _is_confirmation_message(user_message):
        state["context_confirmed"] = True
        state["is_done"] = True
        state["phase"] = QuizPhases.COMPLETED
        state["current_response"] = "Perfetto. Ho salvato il contesto aziendale definitivo."
        state["messages"].append({"role": "assistant", "content": state["current_response"]})
        return state

    # Fast path: user pasted a full markdown replacement
    if _looks_like_full_markdown(user_message):
        state["final_markdown"] = user_message.strip()
        state["current_response"] = (
            "Ricevuto. Ho aggiornato il testo con la tua versione. "
            "Se è tutto corretto scrivi: \"OK, salva\"."
        )
        state["messages"].append({"role": "assistant", "content": state["current_response"]})
        state["turn_count"] += 1
        return state

    llm = get_llm(temperature=0.2)
    structured_llm = llm.with_structured_output(ContextEditResponse, method="function_calling")

    current_markdown = state.get("final_markdown") or ""
    user_prompt = EDIT_CONTEXT_USER_PROMPT_TEMPLATE.format(
        current_markdown=current_markdown,
        user_request=user_message,
    )

    try:
        response: ContextEditResponse = structured_llm.invoke([
            {"role": "system", "content": EDIT_CONTEXT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ])

        state["final_markdown"] = (response.updated_markdown or current_markdown).strip()
        state["current_response"] = response.answer

        if response.is_confirmed:
            state["context_confirmed"] = True
            state["is_done"] = True
            state["phase"] = QuizPhases.COMPLETED

        state["messages"].append({"role": "assistant", "content": state["current_response"]})
        state["turn_count"] += 1
        return state
    except Exception as e:
        state["error"] = str(e)
        state["current_response"] = "Non sono riuscito ad applicare la modifica. Puoi riprovare in modo più specifico?"
        state["messages"].append({"role": "assistant", "content": state["current_response"]})
        state["turn_count"] += 1
        return state

