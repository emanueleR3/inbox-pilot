from fastapi import HTTPException
from automations.api.services.quiz_service import (
    create_session,
    get_session,
    delete_session,
    append_quiz_answer,
    persist_quiz_result,
    get_session_keys,
)
from automations.api.handler_exception import (
    QuizEmailRequiredException,
    QuizErrorAppendingAnswerException,
    QuizErrorFinishingException,
    QuizErrorGettingStateException,
    QuizErrorListingSessionsException,
    QuizErrorPersistingResultException,
    QuizErrorStartingException,
    QuizErrorSubmittingAnswerException,
    QuizNoQuestionsToAnswerException,
    QuizServiceIdRequiredException,
    QuizSessionAndAnswerRequiredException,
    QuizSessionIdRequiredException,
    QuizSessionNotFoundException,
)
from automations.quiz.models import Question, Answer


class QuizController:
    """Controller che gestisce il flusso del quiz e le eccezioni HTTP"""

    def start_quiz(self, service_id: str):
        if not service_id:
            raise QuizServiceIdRequiredException()

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
            raise QuizErrorStartingException(e)

    def submit_answer(self, session_id: str, email: str, value: str):

        if not session_id or not value:
            raise QuizSessionAndAnswerRequiredException()

        if not email:
            raise QuizEmailRequiredException()

        try:
            sess = get_session(session_id)
            if not sess:
                raise QuizSessionNotFoundException()

            if not sess.quiz.questions:
                raise QuizNoQuestionsToAnswerException()

            answer = Answer(question_id=sess.quiz.questions[-1].id, value=value)
            sess.quiz.answers.append(answer)

            try:
                append_quiz_answer(sess.company_id, sess.quiz.questions[-1], answer)
            except Exception:
                raise QuizErrorAppendingAnswerException()

            next_q = sess.chain.generate_next_question(
                sess.quiz.questions, sess.quiz.answers, sess.company_info
            )

            if next_q is None:
                markdown = sess.chain.extract_total_company_info(sess.company_info, sess.quiz)
                try:
                    persist_quiz_result(email, markdown)
                except Exception:
                    raise QuizErrorPersistingResultException()
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
            raise QuizErrorSubmittingAnswerException(e)

    def get_state(self, session_id: str):
        if not session_id:
            raise QuizSessionIdRequiredException()
        try:
            sess = get_session(session_id)
            if not sess:
                raise QuizSessionNotFoundException()
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
            raise QuizErrorGettingStateException(e)

    def finish_quiz(self, session_id: str, email: str):
        if not session_id:
            raise QuizSessionIdRequiredException()
        try:
            sess = get_session(session_id)
            if not sess:
                raise QuizSessionNotFoundException()
                
            if not email:
                raise QuizEmailRequiredException()
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
            raise QuizErrorFinishingException(e)

    def list_sessions(self):
        try:
            return list(get_session_keys())
        except Exception as e:
            raise QuizErrorListingSessionsException(e)
