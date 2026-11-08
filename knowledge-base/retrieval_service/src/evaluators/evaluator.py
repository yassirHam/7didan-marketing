
from laya import Router

class LayaAnswerEvaluator:

    def __init__(self, threshold: float = 0.5):

        self.router = Router()
        self.threshold = threshold

        self.questions = {
            "answer_valid": {
                "type": "noul",
                "instructions": """
You are evaluating the quality and factual correctness
of an AI-generated answer for Orange Maroc Business.

You will receive:
- The user's question.
- Retrieved documentation.
- The generated answer.

Determine whether the generated answer adequately handles
the user's question using the retrieved documentation.

Evaluation criteria:

1. Question coverage:
   Does the answer address the specific information requested?

2. Factual grounding:
   Are the factual claims supported by the retrieved context?

3. Completeness:
   Does the answer provide the requested information
   with sufficient detail?

4. Unsupported information:
   Does the answer invent prices, specifications,
   conditions, or other facts not supported by the context?

5. Appropriate abstention:
   If the documentation does not contain sufficient
   information, does the answer clearly acknowledge
   this limitation instead of inventing information?

Decision:

Return TRUE if:
- The answer adequately addresses the question.
- Its factual claims are supported by the context.
- Or it correctly abstains because the context
  does not contain sufficient information.

Return FALSE if:
- The answer does not address the requested information.
- It provides unsupported or fabricated claims.
- It gives an incorrect or incomplete answer without
  acknowledging the missing information.
- It refuses to answer despite sufficient evidence
  being available in the context.

Do not use external knowledge.
Evaluate only the supplied question, context, and answer.
"""
            }
        }

    def evaluate(
        self,
        question: str,
        context: str,
        answer: str
    ) -> dict:

        state = {
            "question": question,
            "context": context,
            "answer": answer
        }

        result = self.router.predict(
            state=state,
            questions=self.questions,
            max_len=8192
        )

        prediction = result["answers"]["answer_valid"]

        score = float(prediction["noul"])

        return {
            "is_valid": score >= self.threshold,
            "score": score,
            "raw_result": result
        }