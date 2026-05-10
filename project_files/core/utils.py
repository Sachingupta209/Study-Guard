from transformers import pipeline

# Load model once
qg_model = pipeline("text2text-generation", model="iarfmoose/t5-base-question-generator")

def ai_generate_questions(text, num_questions=5):
    """
    Fully smart question generator using T5 model.
    Automatically creates:
    - MCQs
    - Options
    - Correct answers
    """
    questions = []

    # Generate questions
    prompt = f"Generate {num_questions} exam style questions based on this content:\n{text}"
    generated = qg_model(prompt, max_length=128, num_return_sequences=num_questions)

    for item in generated:
        question = item["generated_text"]

        # Generate options
        opt_prompt = f"Generate 4 multiple choice options for this question:\n{question}"
        opt_raw = qg_model(opt_prompt, max_length=80, num_return_sequences=1)[0]["generated_text"]
        options = [line.strip() for line in opt_raw.split("\n") if line.strip()]

        if len(options) < 4:
            options = ["Option A", "Option B", "Option C", "Option D"]

        # Generate correct answer
        ans_prompt = f"Give the correct answer to this question:\n{question}"
        answer = qg_model(ans_prompt, max_length=50, num_return_sequences=1)[0]["generated_text"]

        questions.append({
            "question": question,
            "options": options[:4],
            "correct": answer
        })

    return questions
