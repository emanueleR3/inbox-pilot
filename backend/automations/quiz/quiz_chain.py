from typing import List, Dict, Any, Optional
from datetime import datetime
import os

from langchain_openai import ChatOpenAI

from models import Question, Answer, Quiz, CompanyInfo, Address
from prompts import Prompts
from dotenv import load_dotenv

load_dotenv()


class QuizChain:
    """
    A LangChain-based quiz generation and management system.
    Uses GPT-4o-mini to dynamically generate questions about company information.
    Maximum of 20 questions will be asked.
    """
    
    MAX_QUESTIONS = 5
    
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
    
    def generate_next_question(self, questions: List[Question], answers: List[Answer], company_info: Optional[CompanyInfo] = None) -> Optional[Question]:
        """
        Generate the next question based on previous answers and current company info.
        
        Args:
            questions: List of questions asked so far
            answers: List of previous answers
            company_info: Current state of company information collected
            
        Returns:
            Next Question object or None if quiz is complete
        """
        current_count = len(answers)
        
        # Format history
        history = "\n".join([
            f"Q{i+1}: {questions[i].text}\nA{i+1}: {ans.value}"
            for i, ans in enumerate(answers)
        ]) if answers else "No questions asked yet."
        
        # Format company info
        if company_info:
            company_info_str = company_info.model_dump_json(indent=2, exclude_none=True)
        else:
            company_info_str = "Nessuna informazione raccolta."
        
        # Create the chain with Pydantic parser
        chain = (
            {
                "current_count": lambda _: current_count + 1,
                "max_questions": lambda _: self.MAX_QUESTIONS,
                "history": lambda _: history,
                "company_info": lambda _: company_info_str
            }
            | Prompts.get_question_generator()
            | self.llm
            | Prompts.question_parser
        )
        
        # Generate question
        try:
            result: Question = chain.invoke({})
            questions.append(result)
        except Exception as e:
            print(f"Quiz may be complete or error occurred: {e}")
            return None
        
        # Check if done (in case of mixed response)
        if hasattr(result, 'done') and result.done:
            return None
        
        # Result is already a Question object from models.py, return it directly
        return result

    def extract_total_company_info(self, company_info: CompanyInfo, quiz: Quiz) -> str:
        """
        Extract complete company information from previous informations and quiz.
        
        Args:
            company_info: Current state of company information statically collected
            quiz: Quiz object containing questions
            answers: List of answers provided
            
        Returns:
            CompanyInfo object with extracted information in MarkDown format
        """

        answers = quiz.answers
        questions = quiz.questions
        # Format Q&A data
        qa_data = "\n".join([
            f"Q: {questions[i].text}\nA: {answers[i].value}"
            for i in range(len(answers)) if i < len(questions)
        ]) if answers else "No data yet."
        
        # Create the extraction chain
        chain = (
            {
                "company_info": lambda _: company_info.model_dump_json(indent=2, exclude_none=True),
                "qa_data": lambda _: qa_data
            }
            | Prompts.get_quiz_info_extractor()
            | self.llm
        )
        
        # Extract company info
        try:
            result = chain.invoke({})
            return result.content if hasattr(result, 'content') else str(result)
        except Exception as e:
            print(f"Error extracting company info: {e}")
            return ""
    
    def run_interactive_quiz(self) -> Quiz:
        """
        Run an interactive quiz session in the console.
        
        Returns:
            Completed Quiz object with all questions and answers
        """
        print(f"=== Company Information Quiz ===")
        print(f"Maximum {self.MAX_QUESTIONS} questions will be asked.\n")
        


        company_address = Address(
            street="Via Roma, 10",
            city="Milano",
            region="Lombardia",
            postal_code="20121",
            country="Italia"
        )
        company_info = CompanyInfo(
            company_name="Soluzioni Tecniche s.r.l.",
            website="https://www.soluzionitecniche.it",
            industry="Tecnologia e servizi industriali",
            opening_hrs="Lun-Ven 09:00-17:00",
            employee_count=35,
            address=company_address,
            products_services="Progettazione, produzione e assistenza tecnica di componenti industriali",
            tone_of_voice="Professionale e cordiale",
            email_address="info@soluzionitecniche.it",
            email_signature="Cordiali saluti,\nSoluzioni Tecniche Team",
            phone_number="+39-02-12345678",
            vat_number="IT12345678901"
        )

        quiz = Quiz(id="company_info_quiz", questions=[])
        quiz_date = datetime.now().strftime("%Y%m%d%H%M")
        company_name_clean = company_info.company_name.replace(" ", "_").replace(".", "").lower()
        answers: List[Answer] = []
        questions: List[Question] = []
        
        while len(answers) < self.MAX_QUESTIONS:
            # Generate next question with current company info
            question = self.generate_next_question(questions, answers, company_info)

            if question is None:
                print("\n✓ Quiz complete!")
                break
            
            quiz.questions.append(question)
            
            # Display question
            print(f"\nQuestion {len(answers) + 1}/{self.MAX_QUESTIONS}")
            print(f"{question.text}")
            
            if question.helper_text:
                print(f"  ({question.helper_text})")
            
            # Get answer
            value = input("Your answer: ").strip()
            
            # Store answer
            answer = Answer(question_id=question.id, value=value)
            answers.append(answer)
            quiz.answers = answers

            with open(f"automations/informations_setup/logs/{company_name_clean}_{quiz_date}_quiz.log", "a") as log_file:
                log_file.write(f"Q: {question.text}\nA: {value}\n\n")

            print(f"✓ Answer recorded: {value}")

        # After quiz completion, extract final company info and save to markdown
        company_info_md = self.extract_total_company_info(company_info, quiz)

        # Save the company info to a markdown file
        with open(f"automations/informations_setup/logs/{company_name_clean}_{quiz_date}_info_.md", "w") as md_file:
            md_file.write(company_info_md)

        return quiz


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
