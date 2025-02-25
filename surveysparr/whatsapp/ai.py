from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# Load free Hugging Face chatbot model (DialoGPT)
tokenizer = AutoTokenizer.from_pretrained("microsoft/DialoGPT-medium")
model = AutoModelForCausalLM.from_pretrained("microsoft/DialoGPT-medium")

def generate_huggingface_response(message):
    inputs = tokenizer.encode(message + tokenizer.eos_token, return_tensors="pt")
    reply_ids = model.generate(inputs, max_length=1000, pad_token_id=tokenizer.eos_token_id)
    response = tokenizer.decode(reply_ids[:, inputs.shape[-1]:][0], skip_special_tokens=True)
    return response

print(generate_huggingface_response("What are your working hours?"))
