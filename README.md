# Personal AI Communication Assistant

## Methodology

### 1. Smart Email Management (Gmail)
- **Email Categorization**: Utilized Gmail API with Google OAuth 2.0 authentication to fetch emails. Labeled emails using NLP techniques and trained a Random Forest model, then applied the saved model for categorization.
- **Summarization**: Implemented the T5 Transformer model (via Hugging Face’s pipeline API) for email summarization.
- **Quick Responses**: Fine-tuned DialoGPT on a large email response dataset to generate automated replies.
- **Reminders**: Filtered important unread emails using the Gmail query: `is:unread is:important -from:me -in:chats` and leveraged Gmail API’s `send()` method to send reminders.

### 2. Team Communication Optimization (Slack)
- **Message Processing**: Integrated Slack API for message retrieval and used a Slack Bot Token for authentication.
- **Summarization & Digests**: Employed `facebook/bart-large-cnn` for summarizing key discussions. The BART model extracts key topics, while keyword-based processing identifies action items.
- **Task Extraction**: Applied spaCy NLP to detect tasks based on predefined action keywords and urgency indicators.
- **Smart Search**: Converted messages into vector embeddings using a Transformer model and indexed them with FAISS for fast similarity search.

### 3. WhatsApp Automation
- **Routine Responses**: Fine-tuned DialoGPT using WhatsApp chat history (JSON dataset) for automated responses.
- **Chat Summarization**: Applied a pre-trained BART model to summarize long conversations.
- **Follow-ups & Reminders**: Used Chrome WebDriver to search contacts and send messages via WhatsApp Web. Implemented Python Scheduler to run reminders in a separate thread for scheduled message sending.

## Findings & Recommendations
- **Email Categorization**: Initially used clustering-based labeling, then improved accuracy by combining NLP tools with a keyword-based approach and a Random Forest model.
- **Slack Task Extraction**: Enhanced task identification by combining keyword-based techniques with NLP methods.
- **WhatsApp Automation**: Explored API-based solutions initially, then transitioned to Selenium-based automation, addressing challenges like scrolling and "Read more" expansion.
