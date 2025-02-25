from transformers import pipeline

# Load a free AI chatbot model for text generation
chatbot = pipeline("text-generation", model="facebook/blenderbot-400M-distill")

# Test chatbot with general messages
while True:
    user_input = input("You: ")
    if user_input.lower() in ["exit", "quit"]:
        print("Chatbot stopped.")
        break

    response = chatbot(user_input, max_length=100, do_sample=True)
    print(f"Bot: {response[0]['generated_text']}")
