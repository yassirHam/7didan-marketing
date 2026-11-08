from pydantic import BaseModel, Field
from typing import Literal
from langchain_core.prompts import ChatPromptTemplate,PromptTemplate


class GuardrailDecision(BaseModel):
    status: Literal["allowed", "rejected"] = Field(
        description="Whether the question is allowed."
    )


class InputGuardrail:

    def __init__(self, llm,prompt_file:str):

        structured_llm = llm.with_structured_output(
            GuardrailDecision
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system",PromptTemplate.from_file(prompt_file).template),
            ("human", "{question}")
        ])

        self.chain = prompt | structured_llm

    def validate(self, question: str) -> bool:

        result = self.chain.invoke({
            "question": question
        })

        return result.status == "allowed"