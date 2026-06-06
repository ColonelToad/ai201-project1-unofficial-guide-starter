import os
import chromadb
from groq import Groq
import gradio as gr
from dotenv import load_dotenv
from chromadb.utils import embedding_functions

# Load environment variables from .env file
load_dotenv()

# Initialize Client connections
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# Load embedding function configuration to pull the exact collection indexed in Milestone 4
embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)
collection = chroma_client.get_collection(
    name="knights_circle_reviews", 
    embedding_function=embedding_func
)

def ask_rag_system(query: str, k: int = 5):
    """
    Retrieves relevant chunks from ChromaDB, analyzes distance constraints, 
    and pipes context with ironclad system boundaries to Groq's Llama-3.3 model.
    """
    # 1. Retrieve raw contexts from ChromaDB
    results = collection.query(query_texts=[query], n_results=k)
    
    documents = results['documents'][0]
    metadatas = results['metadatas'][0]
    distances = results['distances'][0]
    
    # 2. Programmatically track and structure context and sources
    context_blocks = []
    formatted_sources = []
    
    # Track unique sources to prevent UI pollution
    seen_sources = set()
    
    # If the closest match is mathematically extremely weak, catch it
    # Cosine distance > 0.65 suggests no high-fidelity matching text exists
    is_weak_match = distances[0] > 0.65
    
    for doc, meta, dist in zip(documents, metadatas, distances):
        # Format block string for the LLM context prompt
        block = (
            f"Source File: {meta['filename']}\n"
            f"Phase Context: {meta['phase']}\n"
            f"Review Date: {meta['date']}\n"
            f"Review Text: {doc}\n"
            "-----------------------"
        )
        context_blocks.append(block)
        
        # Build clean string representation for the user UI view
        source_key = f"File: {meta['filename']} | Phase: {meta['phase']} (Date: {meta['date']})"
        if source_key not in seen_sources:
            seen_sources.add(source_key)
            formatted_sources.append(f"• {source_key} [Distance: {dist:.3f}]")

    full_context = "\n\n".join(context_blocks)
    
    # 3. System prompt construction focusing on exact constraints
    system_prompt = (
        "You are 'The Unofficial Guide' AI assistant for UCF student housing. Your task is to answer "
        "the user's question using ONLY the provided student review snippets.\n\n"
        "STRICT COMPLIANCE DIRECTIVES:\n"
        "1. Base your answer purely on the context snippets provided. Never use external or general "
        "pre-trained knowledge about UCF or apartment layouts.\n"
        "2. If the snippets do not contain the answer, or if the context is completely sparse regarding "
        "the specific query, state: 'I don't have enough verified student documentation to answer this question accurately.'\n"
        "3. Explicitly look past student profanity, casual cursing, or highly emotional phrasing to focus entirely on the "
        "substantive factual claims (e.g., if a resident says 'it fucking sucks because the AC broke twice', focus on chronic AC breakdown).\n"
        "4. Pay close attention to dates and phases. Synthesize timelines clearly (e.g., 'A review from 2022 notes X, but later details show Y').\n"
        "5. If there is an extreme mismatch between the question and the data (such as the user asking about Phase 1, "
        "but the context chunks only explicitly detail Phase 3 with weak similarity metrics), explicitly call out "
        "the data discrepancy in your response instead of lumping them together blindly."
    )
    
    user_prompt = f"Context Documents:\n{full_context}\n\nUser Question: {query}"
    
    # 4. Request completion payload via Groq
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0,  # Forces extreme determinism to stop hallucinations
            max_tokens=800
        )
        answer = completion.choices[0].message.content
    except Exception as e:
        answer = f"Error during generation step: {str(e)}"
        
    return {
        "answer": answer,
        "sources": formatted_sources
    }


# 5. Gradio UI Interface definition matching instructions layout
def handle_interface_query(question):
    if not question.strip():
        return "Please input a valid question.", ""
    
    result = ask_rag_system(question)
    sources_text = "\n".join(result["sources"])
    return result["answer"], sources_text

with gr.Blocks(title="Knights Circle Unofficial Guide") as demo:
    gr.Markdown("# ⚔️ The Unofficial Guide: Knights Circle (UCF)")
    gr.Markdown(
        "Ask plain-language questions about living conditions, towing policies, or maintenance issues "
        "drawn strictly from student reviews from Reddit discussions."
    )
    
    with gr.Row():
        with gr.Column():
            inp = gr.Textbox(
                label="Your Question", 
                placeholder="e.g., What should a student know about visitor parking and towing costs?",
                lines=2
            )
            btn = gr.Button("Submit Query", variant="primary")
        
    with gr.Row():
        with gr.Column():
            answer_box = gr.Textbox(label="Grounded System Answer", lines=10, interactive=False)
            sources_box = gr.Textbox(label="Retrieved Document Evidence", lines=5, interactive=False)
            
    # Hook click events programmatically
    btn.click(handle_interface_query, inputs=inp, outputs=[answer_box, sources_box])
    inp.submit(handle_interface_query, inputs=inp, outputs=[answer_box, sources_box])

if __name__ == "__main__":
    # Launch local server
    demo.launch(server_name="127.0.0.1", server_port=7860)