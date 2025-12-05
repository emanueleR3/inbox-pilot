from fastapi import HTTPException, status
from automations.api.services.quiz_service import (
    create_session,
    get_session,
    delete_session,
    append_quiz_answer,
    persist_quiz_result,
    get_session_keys,
)
from automations.quiz.models import Question, Answer


class QuizController:
    """Controller che gestisce il flusso del quiz e le eccezioni HTTP"""

    def start_quiz(self, service_id: str):
        if not service_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Service ID richiesto"
            )

        try:
            sess = create_session(service_id)
            question = sess.chain.generate_next_question(
                sess.quiz.questions, sess.quiz.answers, sess.company_info
            )

            return {
                "session_id": sess.session_id,
                "question": {
                    "id": question.id,
                    "text": question.text,
                    "helper_text": question.helper_text,
                    "order": question.order,
                } if question else None,
                "max_questions": sess.chain.max_questions,
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Errore durante l'avvio del quiz: {str(e)}"
            )

    def submit_answer(self, session_id: str, email: str, value: str):

        if not session_id or not value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session ID e risposta sono obbligatori"
            )

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email richiesta"
            )

        try:
            sess = get_session(session_id)
            if not sess:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Sessione non trovata"
                )

            if not sess.quiz.questions:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Nessuna domanda da rispondere. Avvia prima il quiz."
                )

            answer = Answer(question_id=sess.quiz.questions[-1].id, value=value)
            sess.quiz.answers.append(answer)

            try:
                append_quiz_answer(sess.company_id, sess.quiz.questions[-1], answer)
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Errore durante l'aggiunta della risposta al quiz"
                )

            next_q = sess.chain.generate_next_question(
                sess.quiz.questions, sess.quiz.answers, sess.company_info
            )

            if next_q is None:
                markdown = sess.chain.extract_total_company_info(sess.company_info, sess.quiz)
                try:
                    persist_quiz_result(email, markdown)
                except Exception:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Errore durante la persistenza del risultato del quiz"
                    )
                delete_session(sess.session_id)
                return {
                    "done": True,
                    "extracted_markdown": markdown,
                    "total_answers": len(sess.quiz.answers),
                }

            return {
                "done": False,
                "next_question": {
                    "id": next_q.id,
                    "text": next_q.text,
                    "helper_text": next_q.helper_text,
                    "order": next_q.order,
                },
                "total_answers": len(sess.quiz.answers),
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Errore durante l'invio della risposta: {str(e)}"
            )

    def get_state(self, session_id: str):
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session ID richiesto"
            )
        try:
            sess = get_session(session_id)
            if not sess:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Sessione non trovata"
                )
            return {
                "session_id": session_id,
                "questions": [
                    {
                        "id": q.id,
                        "text": q.text,
                        "helper_text": q.helper_text,
                        "order": q.order,
                    } for q in sess.quiz.questions
                ],
                "answers": [str(a.value) for a in sess.quiz.answers],
                "total": len(sess.quiz.answers),
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Errore durante il recupero dello stato: {str(e)}"
            )

    def finish_quiz(self, session_id: str, email: str):
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session ID richiesto"
            )
        try:
            sess = get_session(session_id)
            if not sess:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Sessione non trovata"
                )
                
            if not email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email richiesta"
                )
            markdown = sess.chain.extract_total_company_info(sess.company_info, sess.quiz)
            try:
                persist_quiz_result(email, markdown)
            except Exception:
                pass
            delete_session(sess.session_id)
            return {"extracted_markdown": markdown}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Errore durante la conclusione del quiz: {str(e)}"
            )

    def list_sessions(self):
        try:
            return list(get_session_keys())
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Errore durante il recupero delle sessioni: {str(e)}"
            )
