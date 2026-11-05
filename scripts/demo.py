from fitness_assistant.rag import rag


if __name__ == "__main__":
    question = "Is the Lat Pulldown considered a strength training activity, and if so, why?"
    answer_data = rag(question)
    print(answer_data["answer"])
