"""
Core workflow nodes for the quiz system.
"""

import os
import re
from typing import List, Tuple, Optional
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
    INITIAL_QUESTION,
    WITH_CONTEXT_TODO_MESSAGE,
)

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

    # Domain shortcut: RSA / casa di riposo / struttura per anziani
    business_lower = (business_description or "").lower()
    rsa_keywords = [
        "rsa",
        "residenza sanitaria assistenziale",
        "casa di riposo",
        "struttura per anziani",
        "anziani",
    ]

    if any(k in business_lower for k in rsa_keywords):
        print("   🏥 Detected RSA domain, using curated plan")
        curated = [
            "Servizi sanitari e assistenziali",
            "Assistenza medica e infermieristica (H24)",
            "Rette, costi e cosa include",
            "Accreditamento ASL e quota coperta",
            "Processo di ammissione",
            "Tipologie di camere e servizi inclusi",
            "Orari visite e modalità di accesso",
            "Attività ricreative e socializzazione",
            "Personale e qualifiche",
            "Sicurezza, igiene e gestione farmaci",
        ]

        state["bullet_list"] = [{"name": name, "completed": False, "info": None} for name in curated]
        first_question = "Quali servizi sanitari e assistenziali offrite agli ospiti?"
        state["current_response"] = first_question
        state["phase"] = QuizPhases.COLLECTING
        state["messages"].append({
            "role": "assistant",
            "content": first_question,
        })
        state["turn_count"] += 1

        print(f"   ✅ Curated plan generated with {len(curated)} categories")
        for item in curated:
            print(f"      - {item}")
        return state
    
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
        
        # Convert to state format
        bullet_list: List[BulletItem] = [
            {"name": item.name, "completed": False, "info": None}
            for item in response.bullet_list
        ]
        
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
                return f"Perfetto. Per completare il profilo mi serve anche: {next_cat}. Mi dai qualche dettaglio?"
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

        final_answer = _fallback_next_question(updated_bullet_list) if should_override_question else proposed_answer

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
    # TODO: Implement this case
    # This should:
    # 1. Query the qdrant collection to get context about the company
    # 2. Use the context to generate more targeted questions
    # 3. Pre-fill some information from the scraped content
    # 4. Ask only clarifying questions for missing information
    
    print(f"🔮 [WITH_CONTEXT] User has qdrant collection: {state['qdrant_collection_name']}")
    print(f"   ⚠️ TODO: Implement RAG-based quiz flow")
    
    # For now, mark as done and return empty
    state["is_done"] = True
    state["phase"] = QuizPhases.COMPLETED
    state["current_response"] = WITH_CONTEXT_TODO_MESSAGE
    state["final_markdown"] = ""
    
    return state
