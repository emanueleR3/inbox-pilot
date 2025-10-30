"""
Prompts for the QuizChain system.
Centralized prompt management for better maintainability and flexibility.
"""

# TODO Orientare i prompt verso la raccolta di informazioni utili a rispondere ad email in ingresso 
# all'azienda. Attualmente i prompt si focalizzano sulla raccolta di informazioni aziendali.

from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from models import Question, CompanyInfo


class Prompts:
    """
    Collection of prompts used in the quiz system.
    Uses PydanticOutputParser for automatic format instruction generation.
    """
    
    # Create parsers - using Question model from models.py
    question_parser = PydanticOutputParser(pydantic_object=Question)
    
    @staticmethod
    def get_question_generator() -> ChatPromptTemplate:
        """
        Get the question generator prompt with format instructions.
        """
        return ChatPromptTemplate.from_messages([
            ("system", """**Sei un esperto nella raccolta di informazioni aziendali finalizzate alla generazione automatica di risposte email.
Il tuo compito è condurre un quiz dinamico che profili l’azienda ponendo domande mirate, con l’obiettivo di raccogliere tutte le informazioni necessarie affinché un modello linguistico possa rispondere in modo autonomo, coerente e accurato alle email in arrivo per conto dell’azienda.**

## Linee guida per la generazione della prossima domanda
1. Scopo principale: ogni domanda deve mirare a ottenere informazioni che saranno direttamente utili per comprendere il tono, i servizi, le politiche, i prodotti o i processi aziendali necessari a redigere risposte email efficaci.
2. Adattività: formula la prossima domanda in base a:
 -Le informazioni statiche già note sull’azienda.
 -Le risposte precedenti, per creare un flusso logico e progressivo.
 -Eventuali lacune informative ancora presenti nel profilo aziendale.
3. Stile delle domande:
 -Chiare, specifiche e orientate all’obiettivo (mai troppo generiche).
 -Formulate in modo naturale, come se fossi un consulente che vuole capire come rappresentare l’azienda nelle comunicazioni.
 -Se opportuno, proponi domande di follow-up per chiarire o approfondire risposte precedenti.
4. Se hai già informazioni sufficienti, restituisci un JSON con "done": true.
             
## Contesto

### Informazioni aziendali statiche:    
{company_info}
### Domande e risposte precedenti:
{history}
### Numero di domande poste: 
{current_count}/{max_questions}
             
{format_instructions}"""),
            ("user", "Genera la prossima domanda.")
        ]).partial(format_instructions=Prompts.question_parser.get_format_instructions())
    
    #TODO metti come input le company info e le q&a, e ottieni come output un markdown completo dell'azienda
    @staticmethod
    def get_quiz_info_extractor() -> ChatPromptTemplate:
        """
        Get the quiz info extraction prompt with format instructions.
        """
        return ChatPromptTemplate.from_messages([
            ("system", """Sei un esperto nella creazione di profili aziendali dettagliati in formato Markdown, progettati per essere utilizzati da un modello AI per rispondere automaticamente alle email aziendali.

Il tuo compito è:
1.	Estrarre tutte le informazioni rilevanti sull’azienda a partire da:
 - Informazioni aziendali statiche fornite.
 - Domande e risposte fornite (da usare come fonte di conoscenza e inferenza, non come FAQ).
2.	Generare un file Markdown completo e strutturato in base a queste informazioni, pronto per essere utilizzato da un modello AI per rispondere alle email."""),
        ("user", """Informazioni aziendali statiche:
{company_info}
         
         Domande e Risposte:
{qa_data}""")
        ])


__all__ = ["Prompts"]
