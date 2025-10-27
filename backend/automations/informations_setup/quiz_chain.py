from typing import List, Dict, Any, Optional
from datetime import datetime
import os

from langchain_openai import ChatOpenAI

from models import Quiz, Question, QuestionType, Option, Answer, CompanyInfo, Address
from prompts import Prompts, ExtractedCompanyInfo
from dotenv import load_dotenv

load_dotenv()


class QuizChain:
    """
    A LangChain-based quiz generation and management system.
    Uses GPT-4o-mini to dynamically generate questions about company information.
    Maximum of 20 questions will be asked.
    """
    
    MAX_QUESTIONS = 20
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the QuizChain with GPT-4o-mini model.
        
        Args:
            api_key: OpenAI API key. If not provided, uses OPENAI_API_KEY env variable.
        """
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            api_key=api_key or os.getenv("OPENAI_API_KEY")
        )
        
    def should_continue(self, current_count: int, answers: List[Answer]) -> bool:
        """
        Determine if we should continue asking questions.
        
        Args:
            current_count: Number of questions asked so far
            answers: List of answers collected
            
        Returns:
            True if should continue, False otherwise
        """
        if current_count >= self.MAX_QUESTIONS:
            return False
        
        # TODO Could add logic to check if we have minimum required info, examining answers
        return True
    
    def generate_next_question(self, answers: List[Answer]) -> Optional[Question]:
        """
        Generate the next question based on previous answers.
        
        Args:
            answers: List of previous answers
            
        Returns:
            Next Question object or None if quiz is complete
        """
        current_count = len(answers)
        
        if not self.should_continue(current_count, answers):
            return None
        
        # Format history
        history = "\n".join([
            f"Q{i+1}: {ans.question_id} = {ans.value}"
            for i, ans in enumerate(answers)
        ]) if answers else "No questions asked yet."
        
        # Create the chain with Pydantic parser
        chain = (
            {
                "current_count": lambda _: current_count + 1,
                "max_questions": lambda _: self.MAX_QUESTIONS,
                "history": lambda _: history
            }
            | Prompts.get_question_generator()
            | self.llm
            | Prompts.question_parser
        )
        
        # Generate question
        try:
            result: Question = chain.invoke({})
        except Exception as e:
            # Try to detect completion signal
            print(f"Quiz may be complete or error occurred: {e}")
            return None
        
        # Check if done (in case of mixed response)
        if hasattr(result, 'done') and result.done:
            return None
        
        # Result is already a Question object from models.py, return it directly
        return result
    
    def run_interactive_quiz(self) -> Quiz:
        """
        Run an interactive quiz session in the console.
        
        Returns:
            Completed Quiz object with all questions and answers
        """
        print(f"=== Company Information Quiz ===")
        print(f"Maximum {self.MAX_QUESTIONS} questions will be asked.\n")
        
        quiz = Quiz(id="company_info_quiz", questions=[])
        answers: List[Answer] = []
        
        while len(answers) < self.MAX_QUESTIONS:
            # Generate next question
            question = self.generate_next_question(answers)
            
            if question is None:
                print("\n✓ Quiz complete!")
                break
            
            quiz.questions.append(question)
            
            # Display question
            print(f"\nQuestion {len(answers) + 1}/{self.MAX_QUESTIONS}")
            print(f"{question.text}")
            
            if question.helper_text:
                print(f"  ({question.helper_text})")
            
            # Display options if applicable
            if question.options:
                for opt in question.options:
                    print(f"  - {opt.id}: {opt.value}")
            
            # Get answer
            if question.type == QuestionType.CHOICE_MULTI:
                user_input = input("Your answer (comma-separated option IDs): ").strip()
                value = [v.strip() for v in user_input.split(",")]
            else:
                user_input = input("Your answer: ").strip()
                value = user_input
            
            # Store answer
            answer = Answer(question_id=question.id, value=value)
            answers.append(answer)
            
            print(f"✓ Answer recorded: {value}")
        
        return quiz
    
    def extract_company_info(self, quiz: Quiz, answers: List[Answer]) -> CompanyInfo:
        """
        Extract structured CompanyInfo from quiz answers using LLM.
        
        Args:
            quiz: The quiz object with questions
            answers: List of answers provided
            
        Returns:
            CompanyInfo object populated with extracted data
        """
        # Format Q&A data
        qa_data = []
        answer_dict = {a.question_id: a.value for a in answers}
        for q in quiz.questions:
            if q.id in answer_dict:
                qa_data.append(f"Q: {q.text}\nA: {answer_dict[q.id]}")
        
        qa_text = "\n\n".join(qa_data)
        
        # Use Pydantic parser for structured extraction
        chain = Prompts.get_company_info_extractor() | self.llm | Prompts.company_info_parser
        result: ExtractedCompanyInfo = chain.invoke({"qa_data": qa_text})
        
        # Convert ExtractedCompanyInfo to CompanyInfo
        address = Address(
            street=result.address_street,
            city=result.address_city,
            region=result.address_region,
            postal_code=result.address_postal_code,
            country=result.address_country
        ) if any([result.address_street, result.address_city, result.address_region, 
                  result.address_postal_code, result.address_country]) else None
        
        company_info = CompanyInfo(
            company_name=result.company_name,
            website=result.website,
            industry=result.industry,
            opening_hrs=result.opening_hrs,
            employee_count=result.employee_count,
            address=address,
            products_services=result.products_services,
            tone_of_voice=result.tone_of_voice,
            email_address=result.email_address,
            email_signature=result.email_signature,
            phone_number=result.phone_number,
            vat_number=result.vat_number
        )
        
        return company_info


def main():
    """
    Example usage of the QuizChain.
    """
    # Initialize the quiz chain
    quiz_chain = QuizChain()
    
    # Run interactive quiz
    quiz = quiz_chain.run_interactive_quiz()
    
    # Print summary
    print("\n" + "="*50)
    print(f"Quiz Summary: {len(quiz.questions)} questions asked")
    print("="*50)
    
    # Note: To extract company info, you'd need the answers list
    # This is just a demonstration
    print("\nQuiz completed successfully!")


if __name__ == "__main__":
    main()
