import json
import torch
from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer
with open("whatsapp_chat_data.json", "r", encoding="utf-8") as file:
    chat_data = json.load(file)["whatsapp_business_chats"]

formatted_data = {"input": [], "response": []}
for chat in chat_data:
    formatted_data["input"].append(chat["input"])
    formatted_data["response"].append(chat["response"])

dataset = Dataset.from_dict(formatted_data)

# 🔹 Step 3: Load Pretrained DialoGPT Model 
model_name = "microsoft/DialoGPT-medium"  
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)
tokenizer.pad_token = tokenizer.eos_token


def tokenize_function(examples):
    # Format for DialoGPT: input + eos_token + response + eos_token
    conversations = []
    for input_text, response_text in zip(examples["input"], examples["response"]):
        conversation = f"{input_text}{tokenizer.eos_token}{response_text}{tokenizer.eos_token}"
        conversations.append(conversation)
    
    # Tokenize with appropriate padding and truncation
    encodings = tokenizer(
        conversations,
        truncation=True,
        max_length=512,
        padding="max_length",
        return_tensors=None  
    )
    
    # Set labels to input_ids (for causal language modeling)
    encodings["labels"] = encodings["input_ids"].copy()
    
    return encodings

# 🔹 Step 5: Process the dataset
tokenized_dataset = dataset.map(
    tokenize_function,
    batched=True,
    batch_size=16,  # Process multiple examples at once
    remove_columns=dataset.column_names  # Remove original text columns
)

# 🔹 Step 6: Split into training and evaluation sets
train_size = int(0.8 * len(tokenized_dataset))
train_dataset = tokenized_dataset.select(range(train_size))
eval_dataset = tokenized_dataset.select(range(train_size, len(tokenized_dataset)))

# 🔹 Step 7: Define Training Arguments
training_args = TrainingArguments(
    output_dir="./fine_tuned_dialoGPT",
    eval_strategy="epoch",  # Updated parameter name
    save_strategy="epoch",
    per_device_train_batch_size=2,
    per_device_eval_batch_size=2,
    num_train_epochs=3,
    logging_dir="./logs",
    logging_steps=100,
    save_total_limit=2,
    load_best_model_at_end=True,
    weight_decay=0.01,
    warmup_steps=100,
    fp16=False,  
)

# 🔹 Step 8: Initialize Trainer and Train the Model
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
)

trainer.train()

# 🔹 Step 9: Save the Fine-Tuned Model
model.save_pretrained("./fine_tuned_dialoGPT")
tokenizer.save_pretrained("./fine_tuned_dialoGPT")

print(" Fine-tuned model saved successfully!")

def generate_response(input_text):
    # Encode the input text
    input_ids = tokenizer.encode(input_text + tokenizer.eos_token, return_tensors='pt')
    
    # Create attention mask
    attention_mask = torch.ones_like(input_ids)
    
    # Generate a response
    with torch.no_grad():
        output = model.generate(
            input_ids,
            attention_mask=attention_mask,  # Added attention mask
            max_length=150,
            num_return_sequences=1,
            pad_token_id=tokenizer.eos_token_id,
            temperature=0.7,
            top_k=50,
            top_p=0.9,
            do_sample=True
        )
    
    # Decode the response
    response = tokenizer.decode(output[0], skip_special_tokens=True)
    
    
    if input_text in response:
        response = response.replace(input_text, "").strip()
    
    return response

# Example test
if __name__ == "__main__":
    test_input = "Hello, I need help with my order"
    print(f"Input: {test_input}")
    print(f"Generated response: {generate_response(test_input)}")